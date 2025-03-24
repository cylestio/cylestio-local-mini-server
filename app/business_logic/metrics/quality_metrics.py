"""
Quality Metrics module.

This module provides metric calculators for measuring the quality of AI agent responses.
Each calculator focuses on a specific quality metric for better modularity.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, UTC
import statistics
import re
from sqlalchemy.orm import Session

from app.business_logic.metrics.base import BaseMetricCalculator, metric_registry
from app.models.event import Event


class ResponseComplexityCalculator(BaseMetricCalculator):
    """Calculator for response complexity metrics.
    
    Calculates metrics related to the complexity of responses.
    """
    
    def calculate(self, db: Session, start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None, 
                 agent_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 **kwargs) -> Dict[str, Any]:
        """Calculate response complexity metrics.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            
        Returns:
            Dict containing response complexity metrics:
                - average_tokens_per_response: Average tokens per response
                - average_word_count: Average number of words per response
                - average_sentence_count: Average number of sentences per response
                - average_words_per_sentence: Average words per sentence
                - response_count: Number of responses analyzed
        """
        # Get model response events
        response_events = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id,
            event_types=["model_response"],
            directions=["incoming"]
        )
        
        # Extract metrics
        token_counts = []
        word_counts = []
        sentence_counts = []
        
        for event in response_events:
            if not event.data:
                continue
                
            # Extract response text
            response_text = None
            
            if "response" in event.data and "message" in event.data.get("response", {}):
                response_text = event.data.get("response", {}).get("message", {}).get("content")
            elif "content" in event.data:
                response_text = event.data.get("content")
            elif "text" in event.data:
                response_text = event.data.get("text")
                
            if not response_text or not isinstance(response_text, str):
                continue
                
            # Extract token count from usage data
            token_count = None
            
            if "llm_output" in event.data and "usage" in event.data.get("llm_output", {}):
                usage = event.data.get("llm_output", {}).get("usage", {})
                if "output_tokens" in usage:
                    token_count = usage.get("output_tokens")
                elif "completion_tokens" in usage:
                    token_count = usage.get("completion_tokens")
            
            # Alternative token count location in response metadata
            if token_count is None:
                metadata = event.data.get("response", {}).get("message", {}).get("usage_metadata", {})
                if metadata and "output_tokens" in metadata:
                    token_count = metadata.get("output_tokens")
            
            # Calculate word count and sentence count
            word_count = len(response_text.split())
            
            # Simple sentence splitting by .!?
            sentences = re.split(r'[.!?]+', response_text)
            # Filter out empty sentences
            sentences = [s.strip() for s in sentences if s.strip()]
            sentence_count = len(sentences)
            
            # Store the counts
            if token_count is not None and isinstance(token_count, (int, float)):
                token_counts.append(token_count)
                
            word_counts.append(word_count)
            sentence_counts.append(sentence_count)
        
        # Calculate averages
        avg_tokens_per_response = statistics.mean(token_counts) if token_counts else 0
        avg_word_count = statistics.mean(word_counts) if word_counts else 0
        avg_sentence_count = statistics.mean(sentence_counts) if sentence_counts else 0
        
        # Calculate avg words per sentence
        if avg_sentence_count > 0:
            avg_words_per_sentence = avg_word_count / avg_sentence_count
        else:
            avg_words_per_sentence = 0
        
        return {
            "average_tokens_per_response": avg_tokens_per_response,
            "average_word_count": avg_word_count,
            "average_sentence_count": avg_sentence_count,
            "average_words_per_sentence": avg_words_per_sentence,
            "response_count": len(response_events),
            "responses_with_metrics": len(word_counts)
        }
    
    def get_filtered_events(self, db: Session, start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None,
                           agent_id: Optional[str] = None,
                           session_id: Optional[str] = None,
                           event_types: Optional[List[str]] = None,
                           channels: Optional[List[str]] = None,
                           levels: Optional[List[str]] = None,
                           directions: Optional[List[str]] = None) -> List[Event]:
        """Get filtered events based on parameters with direction filter."""
        query = db.query(Event)
        
        if start_time:
            query = query.filter(Event.timestamp >= start_time)
        
        if end_time:
            query = query.filter(Event.timestamp <= end_time)
        
        if agent_id:
            query = query.filter(Event.agent_id == agent_id)
        
        if session_id:
            query = query.filter(Event.session_id == session_id)
        
        if event_types:
            query = query.filter(Event.event_type.in_(event_types))
        
        if channels:
            query = query.filter(Event.channel.in_(channels))
        
        if levels:
            query = query.filter(Event.level.in_(levels))
            
        if directions:
            query = query.filter(Event.direction.in_(directions))
        
        return query.all()


class ResponseAppropriatenessCalculator(BaseMetricCalculator):
    """Calculator for response appropriateness metrics.
    
    Calculates metrics related to the appropriateness of responses.
    """
    
    def calculate(self, db: Session, start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None, 
                 agent_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 **kwargs) -> Dict[str, Any]:
        """Calculate response appropriateness metrics.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            
        Returns:
            Dict containing response appropriateness metrics:
                - error_response_rate: Rate of responses with errors
                - refusal_rate: Rate of responses with refusals
                - hallucination_rate: Rate of responses with hallucinations
                - response_count: Number of responses analyzed
        """
        # Get model response events
        response_events = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id,
            event_types=["model_response"],
            directions=["incoming"]
        )
        
        # Count different response types
        error_count = 0
        refusal_count = 0
        hallucination_count = 0
        analyzed_count = 0
        
        for event in response_events:
            analyzed = False
            
            if event.data:
                # Check response details for error indicators
                if event.data.get("error") or event.data.get("has_error", False):
                    error_count += 1
                    analyzed = True
                
                # Check content for refusals
                response_text = None
                
                if "response" in event.data and "message" in event.data.get("response", {}):
                    response_text = event.data.get("response", {}).get("message", {}).get("content")
                elif "content" in event.data:
                    response_text = event.data.get("content")
                elif "text" in event.data:
                    response_text = event.data.get("text")
                    
                if response_text and isinstance(response_text, str):
                    # Check for refusal patterns
                    refusal_patterns = [
                        "I can't", "I cannot", "I'm unable to", "I am unable to",
                        "not able to", "against policy", "not allowed to",
                        "I'm not allowed", "I am not allowed", "unable to comply"
                    ]
                    
                    if any(pattern.lower() in response_text.lower() for pattern in refusal_patterns):
                        refusal_count += 1
                        analyzed = True
                    
                # Check for hallucination indicators
                if event.data.get("analysis", {}).get("hallucination_detected", False):
                    hallucination_count += 1
                    analyzed = True
                elif event.data.get("hallucination_detected", False):
                    hallucination_count += 1
                    analyzed = True
                    
                if analyzed:
                    analyzed_count += 1
        
        # Calculate rates
        total_responses = len(response_events)
        
        error_rate = error_count / total_responses if total_responses > 0 else 0
        refusal_rate = refusal_count / total_responses if total_responses > 0 else 0
        hallucination_rate = hallucination_count / total_responses if total_responses > 0 else 0
        
        return {
            "error_response_rate": error_rate,
            "refusal_rate": refusal_rate,
            "hallucination_rate": hallucination_rate,
            "error_count": error_count,
            "refusal_count": refusal_count,
            "hallucination_count": hallucination_count,
            "analyzed_count": analyzed_count,
            "response_count": total_responses
        }
    
    def get_filtered_events(self, db: Session, start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None,
                           agent_id: Optional[str] = None,
                           session_id: Optional[str] = None,
                           event_types: Optional[List[str]] = None,
                           channels: Optional[List[str]] = None,
                           levels: Optional[List[str]] = None,
                           directions: Optional[List[str]] = None) -> List[Event]:
        """Get filtered events based on parameters with direction filter."""
        query = db.query(Event)
        
        if start_time:
            query = query.filter(Event.timestamp >= start_time)
        
        if end_time:
            query = query.filter(Event.timestamp <= end_time)
        
        if agent_id:
            query = query.filter(Event.agent_id == agent_id)
        
        if session_id:
            query = query.filter(Event.session_id == session_id)
        
        if event_types:
            query = query.filter(Event.event_type.in_(event_types))
        
        if channels:
            query = query.filter(Event.channel.in_(channels))
        
        if levels:
            query = query.filter(Event.level.in_(levels))
            
        if directions:
            query = query.filter(Event.direction.in_(directions))
        
        return query.all()


class ContentTypeDistributionCalculator(BaseMetricCalculator):
    """Calculator for content type distribution metrics.
    
    Analyzes the distribution of different content types in responses.
    """
    
    def calculate(self, db: Session, start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None, 
                 agent_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 **kwargs) -> Dict[str, Any]:
        """Calculate content type distribution metrics.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            
        Returns:
            Dict containing content type distribution metrics:
                - code_rate: Rate of responses containing code
                - url_rate: Rate of responses containing URLs
                - list_rate: Rate of responses containing lists
                - json_rate: Rate of responses containing JSON
                - response_count: Number of responses analyzed
        """
        # Get model response events
        response_events = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id,
            event_types=["model_response"],
            directions=["incoming"]
        )
        
        # Count different content types
        code_count = 0
        url_count = 0
        list_count = 0
        json_count = 0
        
        for event in response_events:
            # Extract response text
            response_text = None
            
            if event.data:
                if "response" in event.data and "message" in event.data.get("response", {}):
                    response_text = event.data.get("response", {}).get("message", {}).get("content")
                elif "content" in event.data:
                    response_text = event.data.get("content")
                elif "text" in event.data:
                    response_text = event.data.get("text")
                    
            if not response_text or not isinstance(response_text, str):
                continue
                
            # Check for code blocks (markdown style)
            if re.search(r'```[\w]*\n[\s\S]*?\n```', response_text):
                code_count += 1
                
            # Check for URLs
            if re.search(r'https?://[^\s]+', response_text):
                url_count += 1
                
            # Check for lists (markdown style)
            if re.search(r'^\s*[\*\-\+]\s+.+$', response_text, re.MULTILINE) or \
               re.search(r'^\s*\d+\.\s+.+$', response_text, re.MULTILINE):
                list_count += 1
                
            # Check for JSON content
            if re.search(r'^\s*\{\s*"[^"]+"\s*:', response_text, re.MULTILINE) or \
               re.search(r'^\s*\[\s*\{\s*"[^"]+"\s*:', response_text, re.MULTILINE):
                json_count += 1
        
        # Calculate rates
        total_responses = len(response_events)
        
        code_rate = code_count / total_responses if total_responses > 0 else 0
        url_rate = url_count / total_responses if total_responses > 0 else 0
        list_rate = list_count / total_responses if total_responses > 0 else 0
        json_rate = json_count / total_responses if total_responses > 0 else 0
        
        return {
            "code_rate": code_rate,
            "url_rate": url_rate,
            "list_rate": list_rate,
            "json_rate": json_rate,
            "code_count": code_count,
            "url_count": url_count,
            "list_count": list_count,
            "json_count": json_count,
            "response_count": total_responses
        }
    
    def get_filtered_events(self, db: Session, start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None,
                           agent_id: Optional[str] = None,
                           session_id: Optional[str] = None,
                           event_types: Optional[List[str]] = None,
                           channels: Optional[List[str]] = None,
                           levels: Optional[List[str]] = None,
                           directions: Optional[List[str]] = None) -> List[Event]:
        """Get filtered events based on parameters with direction filter."""
        query = db.query(Event)
        
        if start_time:
            query = query.filter(Event.timestamp >= start_time)
        
        if end_time:
            query = query.filter(Event.timestamp <= end_time)
        
        if agent_id:
            query = query.filter(Event.agent_id == agent_id)
        
        if session_id:
            query = query.filter(Event.session_id == session_id)
        
        if event_types:
            query = query.filter(Event.event_type.in_(event_types))
        
        if channels:
            query = query.filter(Event.channel.in_(channels))
        
        if levels:
            query = query.filter(Event.level.in_(levels))
            
        if directions:
            query = query.filter(Event.direction.in_(directions))
        
        return query.all()


# Register all calculators
metric_registry.register(ResponseComplexityCalculator())
metric_registry.register(ResponseAppropriatenessCalculator())
metric_registry.register(ContentTypeDistributionCalculator()) 