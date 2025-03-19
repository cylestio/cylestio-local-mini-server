"""
Error Metrics module.

This module provides metric calculators for error rates and error pattern analysis.
Each calculator focuses on a specific metric for better modularity.
"""

from typing import Dict, Any, Optional, List, Counter
from datetime import datetime, timedelta
from collections import defaultdict
import re
from sqlalchemy.orm import Session

from app.business_logic.metrics.base import BaseMetricCalculator, metric_registry
from app.models.event import Event


class ErrorRateCalculator(BaseMetricCalculator):
    """Calculator for error rate metrics.
    
    Calculates the rate of errors in model responses.
    """
    
    def calculate(self, db: Session, start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None, 
                 agent_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 **kwargs) -> Dict[str, Any]:
        """Calculate error rate metrics.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            
        Returns:
            Dict containing error rate metrics:
                - total_requests: Total number of model requests
                - error_count: Number of error events
                - error_rate: Percentage of requests that resulted in errors
        """
        # Set default time range if not provided
        if not start_time:
            start_time = datetime.utcnow() - timedelta(hours=1)
        
        if not end_time:
            end_time = datetime.utcnow()
            
        # Get model request events
        request_events = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id,
            event_types=["model_request"],
            directions=["outgoing"]
        )
        
        # Get error events
        error_events = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id,
            event_types=["error"],
            levels=["error", "critical"]
        )
        
        # Calculate error rate
        total_requests = len(request_events)
        error_count = len(error_events)
        error_rate = (error_count / total_requests) * 100 if total_requests > 0 else 0
        
        return {
            "total_requests": total_requests,
            "error_count": error_count,
            "error_rate": error_rate
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


class ErrorTrendCalculator(BaseMetricCalculator):
    """Calculator for error trends over time.
    
    Calculates how error rates change over different time intervals.
    """
    
    def calculate(self, db: Session, start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None, 
                 agent_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 interval: str = 'hour',
                 **kwargs) -> Dict[str, Any]:
        """Calculate error trend metrics over time.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            interval: Time interval for grouping ('hour', 'day', 'week')
            
        Returns:
            Dict containing error trend metrics:
                - error_rate_over_time: Error rates grouped by time interval
                - interval: The time interval used for grouping
        """
        # Set default time range if not provided
        if not start_time:
            # Default to last day if no start time
            if interval == 'hour':
                start_time = datetime.utcnow() - timedelta(days=1)
            elif interval == 'day':
                start_time = datetime.utcnow() - timedelta(days=7)
            else:  # 'week'
                start_time = datetime.utcnow() - timedelta(days=30)
        
        if not end_time:
            end_time = datetime.utcnow()
            
        # Format for grouping timestamps by interval
        if interval == 'hour':
            format_str = "%Y-%m-%d %H:00"
            delta = timedelta(hours=1)
        elif interval == 'day':
            format_str = "%Y-%m-%d"
            delta = timedelta(days=1)
        else:  # 'week'
            format_str = "%Y-%W"  # Year and week number
            delta = timedelta(days=7)
            
        # Get model request events
        request_events = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id,
            event_types=["model_request"],
            directions=["outgoing"]
        )
        
        # Get error events
        error_events = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id,
            event_types=["error"],
            levels=["error", "critical"]
        )
        
        # Group requests and errors by interval
        request_counts = defaultdict(int)
        error_counts = defaultdict(int)
        
        for event in request_events:
            interval_key = event.timestamp.strftime(format_str)
            request_counts[interval_key] += 1
            
        for event in error_events:
            interval_key = event.timestamp.strftime(format_str)
            error_counts[interval_key] += 1
            
        # Calculate error rates for each interval
        error_rates = {}
        
        for interval_key, request_count in request_counts.items():
            error_count = error_counts.get(interval_key, 0)
            error_rate = (error_count / request_count) * 100 if request_count > 0 else 0
            error_rates[interval_key] = {
                "requests": request_count,
                "errors": error_count,
                "error_rate": error_rate
            }
            
        # Add intervals with errors but no requests
        for interval_key, error_count in error_counts.items():
            if interval_key not in error_rates:
                error_rates[interval_key] = {
                    "requests": 0,
                    "errors": error_count,
                    "error_rate": 100.0  # 100% error rate if only errors
                }
                
        return {
            "error_rate_over_time": error_rates,
            "interval": interval
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


class ErrorPatternCalculator(BaseMetricCalculator):
    """Calculator for common error patterns.
    
    Identifies and groups common error messages.
    """
    
    def calculate(self, db: Session, start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None, 
                 agent_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 **kwargs) -> Dict[str, Any]:
        """Calculate error pattern metrics.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            
        Returns:
            Dict containing error pattern metrics:
                - common_error_messages: Frequency of common error messages
                - error_count: Total number of error events analyzed
        """
        # Get error events
        error_events = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id,
            event_types=["error"],
            levels=["error", "critical"]
        )
        
        # Extract error messages and count occurrences
        error_messages = []
        
        for event in error_events:
            message = None
            
            # Try to get error message from different places in the event data
            if event.data:
                # Check for error message in data
                message = event.data.get("message")
                
                # If not found, check nested error information
                if not message and "error" in event.data:
                    error_info = event.data.get("error", {})
                    message = error_info.get("message")
                    
                    # If still not found, check for "detail" or "description"
                    if not message:
                        message = error_info.get("detail") or error_info.get("description")
            
            # Use event message if data doesn't contain error info
            if not message:
                message = event.message
                
            # Add to list if we found a message
            if message:
                # Clean up the message: remove variable parts like IDs, timestamps, etc.
                clean_message = self.clean_error_message(message)
                error_messages.append(clean_message)
        
        # Count message occurrences
        message_counts = Counter(error_messages)
        common_messages = dict(message_counts.most_common())
        
        return {
            "common_error_messages": common_messages,
            "error_count": len(error_events)
        }
    
    def clean_error_message(self, message: str) -> str:
        """Clean error message by removing variable parts."""
        # Replace UUIDs, IDs, and other variable parts with placeholders
        cleaned = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '<id>', message)
        cleaned = re.sub(r'\b\d+\b', '<number>', cleaned)
        cleaned = re.sub(r'\b[0-9a-f]{24}\b', '<id>', cleaned)  # MongoDB ObjectIDs
        cleaned = re.sub(r'\b[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]+)?Z?\b', '<timestamp>', cleaned)  # ISO timestamps
        
        return cleaned

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


class ErrorTypeCalculator(BaseMetricCalculator):
    """Calculator for error types by event type.
    
    Groups errors by the event type that triggered them.
    """
    
    def calculate(self, db: Session, start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None, 
                 agent_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 **kwargs) -> Dict[str, Any]:
        """Calculate error type metrics.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            
        Returns:
            Dict containing error type metrics:
                - errors_by_event_type: Counts of errors grouped by event type
                - total_error_count: Total number of error events
        """
        # Get error events
        error_events = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id,
            event_types=["error"],
            levels=["error", "critical"]
        )
        
        # Group errors by the original event type that caused them
        errors_by_event_type = defaultdict(int)
        
        for event in error_events:
            # Try to extract the original event type from the error event
            original_event_type = "unknown"
            
            if event.data and "original_event" in event.data:
                original_event = event.data.get("original_event", {})
                if isinstance(original_event, dict):
                    original_event_type = original_event.get("event_type", "unknown")
            
            # Increment count for this event type
            errors_by_event_type[original_event_type] += 1
        
        return {
            "errors_by_event_type": dict(errors_by_event_type),
            "total_error_count": len(error_events)
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


class ErrorSeverityDistributionCalculator(BaseMetricCalculator):
    """Calculator for error severity distribution.
    
    Analyzes the distribution of errors by severity level.
    """
    
    def calculate(self, db: Session, start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None, 
                 agent_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 **kwargs) -> Dict[str, Any]:
        """Calculate error severity distribution metrics.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            
        Returns:
            Dict containing error severity metrics:
                - error_level_distribution: Counts of errors by severity level
                - total_error_count: Total number of error events
        """
        # Get error events of all levels
        error_events = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id,
            event_types=["error"]
        )
        
        # Count errors by level
        level_counts = defaultdict(int)
        
        for event in error_events:
            level = event.level or "unknown"
            level_counts[level] += 1
        
        return {
            "error_level_distribution": dict(level_counts),
            "total_error_count": len(error_events)
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


# Register the metric calculators
metric_registry.register(ErrorRateCalculator())
metric_registry.register(ErrorTrendCalculator())
metric_registry.register(ErrorPatternCalculator())
metric_registry.register(ErrorTypeCalculator())
metric_registry.register(ErrorSeverityDistributionCalculator()) 