from typing import Dict, Any, Optional, List, Tuple
import datetime
import logging
import uuid
import json

from app.transformers.base import BaseTransformer
from app.transformers.processors.llm_processor import process_llm_call_start, process_llm_call_finish
from app.transformers.processors.tool_processor import process_tool_call_start, process_tool_call_finish
from app.transformers.processors.security_processor import process_security_event
from app.transformers.processors.system_processor import process_system_event

logger = logging.getLogger(__name__)

class EventTransformer(BaseTransformer):
    """
    Main transformer for processing raw JSON events into structured data.
    This transformer handles different event types and extracts common fields.
    """
    
    def _register_processors(self) -> None:
        """
        Register all event processors for different event types.
        """
        # LLM event processors
        self.event_processors["LLM_call_start"] = process_llm_call_start
        self.event_processors["LLM_call_finish"] = process_llm_call_finish
        self.event_processors["LLM_call_blocked"] = process_security_event
        self.event_processors["LLM_patch"] = process_system_event
        
        # Tool event processors
        self.event_processors["call_start"] = process_tool_call_start
        self.event_processors["call_finish"] = process_tool_call_finish
        
        # System event processors
        self.event_processors["monitoring_enabled"] = process_system_event
        self.event_processors["monitoring_disabled"] = process_system_event
        self.event_processors["MCP_patch"] = process_system_event
        
        # Security event processors
        self.event_processors["security_alert"] = process_security_event
    
    def process_batch(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process a batch of events and track relationships between them.
        
        Args:
            events: List of raw JSON events
        
        Returns:
            List of transformed events with relationship data
        """
        # Normalize all timestamps first to avoid type mismatches
        normalized_events = []
        for event in events:
            try:
                normalized = self._normalize_timestamps(event)
                normalized_events.append(normalized)
            except Exception as e:
                logger.error(f"Error normalizing event timestamps: {str(e)}")
                # Still include the original event to avoid data loss
                normalized_events.append(event)
        
        transformed_events = []
        
        # First pass: transform individual events
        for event in normalized_events:
            transformed = self.transform(event)
            transformed_events.append(transformed)
        
        # Second pass: identify relationships
        self._identify_relationships(transformed_events)
        
        return transformed_events
    
    def _normalize_timestamps(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize all timestamp fields in the event to ensure they are in a consistent format.
        
        Args:
            event: Raw event data
            
        Returns:
            Event with normalized timestamps
        """
        # Make a copy to avoid modifying the original
        normalized = event.copy()
        
        # Handle the primary timestamp field
        if "timestamp" in normalized:
            timestamp = normalized["timestamp"]
            if isinstance(timestamp, str):
                # Standardize string timestamp format
                try:
                    normalized["timestamp"] = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                except Exception as e:
                    logger.warning(f"Could not parse timestamp '{timestamp}': {str(e)}")
        
        # Handle nested timestamps in data field
        if "data" in normalized and isinstance(normalized["data"], dict):
            data = normalized["data"].copy()
            
            # Check common timestamp fields in data
            for field in ["timestamp", "patch_time", "start_time", "end_time", "request_time", "response_time"]:
                if field in data and isinstance(data[field], str):
                    try:
                        data[field] = datetime.datetime.fromisoformat(data[field].replace("Z", "+00:00"))
                    except Exception:
                        # Leave as is if parsing fails
                        pass
            
            normalized["data"] = data
        
        return normalized
    
    def _identify_relationships(self, events: List[Dict[str, Any]]) -> None:
        """
        Identify relationships between events such as request/response pairs.
        
        Args:
            events: List of transformed events
            
        Modifies the events in-place to add relationship data.
        """
        # Create lookup tables by event type and agent_id
        llm_starts = {}
        llm_finishes = {}
        tool_starts = {}
        tool_finishes = {}
        
        # First pass: organize events by type
        for i, event in enumerate(events):
            event_type = event.get("event_type")
            agent_id = event.get("agent_id")
            
            # Skip events without a type or agent_id
            if not event_type or not agent_id:
                continue
            
            # Create a less complex composite key - just agent_id and event_counter
            # This avoids timestamp parsing issues completely
            key = f"{agent_id}_{i}"  # Use the index in the array as a simple counter
            
            # Categorize by event type
            if event_type == "LLM_call_start":
                llm_starts[key] = i
            elif event_type == "LLM_call_finish":
                llm_finishes[key] = i
            elif event_type == "call_start":
                tool_starts[key] = i
            elif event_type == "call_finish":
                tool_finishes[key] = i
        
        # Second pass: match request/response pairs
        self._match_request_response_pairs(events, llm_starts, llm_finishes, "LLM")
        self._match_request_response_pairs(events, tool_starts, tool_finishes, "Tool")
            
    def _match_request_response_pairs(
        self, 
        events: List[Dict[str, Any]], 
        starts: Dict[str, int], 
        finishes: Dict[str, int],
        event_category: str
    ) -> None:
        """
        Match request/response pairs for a specific event category.
        
        Args:
            events: List of transformed events
            starts: Dictionary mapping key to index of start events
            finishes: Dictionary mapping key to index of finish events
            event_category: Category name for the events (e.g. "LLM", "Tool")
            
        Modifies the events in-place to add relationship data.
        """
        # For each start event, try to find a matching finish event
        for key, start_idx in starts.items():
            # First extract the agent_id from the start event directly
            agent_id = events[start_idx].get("agent_id")
            if not agent_id:
                continue
                
            # First try: exact key match (most reliable)
            if key in finishes:
                finish_idx = finishes[key]
                self._link_events(events, start_idx, finish_idx)
                continue
                
            # Second try: find any finishes from the same agent
            # Instead of trying to sort by timestamp (which causes string/int problems),
            # we'll collect all finishes for this agent and use a different strategy
            agent_finishes = []
            for finish_key, finish_idx in finishes.items():
                finish_agent_id = events[finish_idx].get("agent_id")
                if finish_agent_id == agent_id:
                    agent_finishes.append((finish_key, finish_idx))
                    
            if not agent_finishes:
                continue  # No matching finishes for this agent
                
            # Strategy: Match events based on positional ordering
            # This avoids problematic string/int comparisons entirely
            # Pick the first unmatched finish event for this agent
            # This assumes events typically arrive in chronological order
            for finish_key, finish_idx in agent_finishes:
                # Check if this finish event is already linked to another start
                if "relationship_id" not in events[finish_idx]:
                    self._link_events(events, start_idx, finish_idx)
                    break
                    
    def _link_events(self, events, start_idx, finish_idx):
        """Helper method to link a start and finish event pair"""
        # Create a relationship ID
        relationship_id = str(uuid.uuid4())
        
        # Update the start event
        events[start_idx]["related_event_id"] = events[finish_idx].get("id")
        events[start_idx]["direction"] = "outgoing"
        events[start_idx]["relationship_id"] = relationship_id
        
        # Update the finish event
        events[finish_idx]["related_event_id"] = events[start_idx].get("id")
        events[finish_idx]["direction"] = "incoming"
        events[finish_idx]["relationship_id"] = relationship_id
        
        # Calculate duration if not already present
        if "duration_ms" not in events[finish_idx] and "timestamp" in events[start_idx] and "timestamp" in events[finish_idx]:
            try:
                start_time = events[start_idx]["timestamp"]
                finish_time = events[finish_idx]["timestamp"]
                
                # Ensure both timestamps are datetime objects
                if isinstance(start_time, str):
                    try:
                        start_time = datetime.datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                    except:
                        # If parsing fails, skip duration calculation
                        return
                        
                if isinstance(finish_time, str):
                    try:
                        finish_time = datetime.datetime.fromisoformat(finish_time.replace("Z", "+00:00"))
                    except:
                        # If parsing fails, skip duration calculation
                        return
                
                if isinstance(start_time, datetime.datetime) and isinstance(finish_time, datetime.datetime):
                    duration_ms = (finish_time - start_time).total_seconds() * 1000
                    events[finish_idx]["duration_ms"] = duration_ms
            except Exception as e:
                logger.error(f"Error calculating duration: {str(e)}") 