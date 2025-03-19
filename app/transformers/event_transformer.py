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
        transformed_events = []
        
        # First pass: transform individual events
        for event in events:
            transformed = self.transform(event)
            transformed_events.append(transformed)
        
        # Second pass: identify relationships
        self._identify_relationships(transformed_events)
        
        return transformed_events
    
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
            
            # Create a composite key from agent_id and timestamp to handle concurrent events
            # We'll use microsecond precision for the timestamp
            timestamp = event.get("timestamp")
            if isinstance(timestamp, datetime.datetime):
                timestamp_str = timestamp.strftime("%Y%m%d%H%M%S%f")
            else:
                timestamp_str = str(timestamp)
            
            key = f"{agent_id}_{timestamp_str}"
            
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
            # Extract agent_id and approximate timestamp from key
            parts = key.split("_")
            agent_id = parts[0]
            time_part = "_".join(parts[1:])
            
            # Find potential matching finish events
            # First, try exact match
            if key in finishes:
                finish_idx = finishes[key]
                
                # Create a relationship ID
                relationship_id = str(uuid.uuid4())
                
                # Update the start event
                events[start_idx]["related_event_id"] = events[finish_idx]["id"] if "id" in events[finish_idx] else None
                events[start_idx]["direction"] = "outgoing"
                events[start_idx]["relationship_id"] = relationship_id
                
                # Update the finish event
                events[finish_idx]["related_event_id"] = events[start_idx]["id"] if "id" in events[start_idx] else None
                events[finish_idx]["direction"] = "incoming"
                events[finish_idx]["relationship_id"] = relationship_id
                
                # Calculate duration if not already present
                if "duration_ms" not in events[finish_idx] and "timestamp" in events[start_idx] and "timestamp" in events[finish_idx]:
                    try:
                        start_time = events[start_idx]["timestamp"]
                        finish_time = events[finish_idx]["timestamp"]
                        if isinstance(start_time, datetime.datetime) and isinstance(finish_time, datetime.datetime):
                            duration_ms = (finish_time - start_time).total_seconds() * 1000
                            events[finish_idx]["duration_ms"] = duration_ms
                    except Exception as e:
                        logger.error(f"Error calculating duration: {str(e)}")
            
            # If no exact match, try to find the closest matching finish event
            # This handles cases where timestamps are not exactly the same
            else:
                # Find finish events from the same agent
                candidate_finishes = []
                for finish_key, finish_idx in finishes.items():
                    if finish_key.startswith(f"{agent_id}_"):
                        candidate_finishes.append((finish_key, finish_idx))
                
                if candidate_finishes:
                    # Sort by time difference (approximate)
                    candidate_finishes.sort(key=lambda x: abs(int(x[0].split("_")[1]) - int(time_part)))
                    
                    # Use the closest one
                    _, finish_idx = candidate_finishes[0]
                    
                    # Create a relationship ID
                    relationship_id = str(uuid.uuid4())
                    
                    # Update the start event
                    events[start_idx]["related_event_id"] = events[finish_idx]["id"] if "id" in events[finish_idx] else None
                    events[start_idx]["direction"] = "outgoing"
                    events[start_idx]["relationship_id"] = relationship_id
                    
                    # Update the finish event
                    events[finish_idx]["related_event_id"] = events[start_idx]["id"] if "id" in events[start_idx] else None
                    events[finish_idx]["direction"] = "incoming"  
                    events[finish_idx]["relationship_id"] = relationship_id
                    
                    # Calculate duration if not already present
                    if "duration_ms" not in events[finish_idx] and "timestamp" in events[start_idx] and "timestamp" in events[finish_idx]:
                        try:
                            start_time = events[start_idx]["timestamp"]
                            finish_time = events[finish_idx]["timestamp"]
                            if isinstance(start_time, datetime.datetime) and isinstance(finish_time, datetime.datetime):
                                duration_ms = (finish_time - start_time).total_seconds() * 1000
                                events[finish_idx]["duration_ms"] = duration_ms
                        except Exception as e:
                            logger.error(f"Error calculating duration: {str(e)}") 