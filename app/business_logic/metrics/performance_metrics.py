"""
Performance Metrics module.

This module provides metric calculators for performance trends and analysis.
Each calculator focuses on a specific metric for better modularity.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import statistics
from sqlalchemy.orm import Session

from app.business_logic.metrics.base import BaseMetricCalculator, metric_registry
from app.models.event import Event


class ResponseTimeCalculator(BaseMetricCalculator):
    """Calculator for response time metrics.
    
    Calculates average response time for model responses.
    """
    
    def calculate(self, db: Session, start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None, 
                 agent_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 **kwargs) -> Dict[str, Any]:
        """Calculate response time metrics.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            
        Returns:
            Dict containing response time metrics:
                - average_response_time_ms: Average response time in milliseconds
                - min_response_time_ms: Minimum response time in milliseconds
                - max_response_time_ms: Maximum response time in milliseconds
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
        
        # Extract response times
        response_times = []
        
        for event in response_events:
            # Extract response time from event data
            response_time = None
            
            if event.data:
                if "duration_ms" in event.data:
                    response_time = event.data.get("duration_ms")
                elif "performance" in event.data and "duration_ms" in event.data.get("performance", {}):
                    response_time = event.data.get("performance", {}).get("duration_ms")
                elif "llm_output" in event.data and "usage" in event.data.get("llm_output", {}):
                    usage = event.data.get("llm_output", {}).get("usage", {})
                    if "response_time_ms" in usage:
                        response_time = usage.get("response_time_ms")
            
            if response_time is not None and isinstance(response_time, (int, float)):
                response_times.append(response_time)
        
        # Calculate statistics
        if response_times:
            average_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
        else:
            average_response_time = 0
            min_response_time = 0
            max_response_time = 0
        
        return {
            "average_response_time_ms": average_response_time,
            "min_response_time_ms": min_response_time,
            "max_response_time_ms": max_response_time,
            "response_count": len(response_times)
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


class ResponseTimePercentileCalculator(BaseMetricCalculator):
    """Calculator for response time percentiles.
    
    Calculates various percentiles of response times.
    """
    
    def calculate(self, db: Session, start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None, 
                 agent_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 **kwargs) -> Dict[str, Any]:
        """Calculate response time percentile metrics.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            
        Returns:
            Dict containing response time percentile metrics:
                - p50_response_time_ms: 50th percentile (median) response time
                - p90_response_time_ms: 90th percentile response time
                - p95_response_time_ms: 95th percentile response time
                - p99_response_time_ms: 99th percentile response time
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
        
        # Extract response times
        response_times = []
        
        for event in response_events:
            # Extract response time from event data
            response_time = None
            
            if event.data:
                if "duration_ms" in event.data:
                    response_time = event.data.get("duration_ms")
                elif "performance" in event.data and "duration_ms" in event.data.get("performance", {}):
                    response_time = event.data.get("performance", {}).get("duration_ms")
                elif "llm_output" in event.data and "usage" in event.data.get("llm_output", {}):
                    usage = event.data.get("llm_output", {}).get("usage", {})
                    if "response_time_ms" in usage:
                        response_time = usage.get("response_time_ms")
            
            if response_time is not None and isinstance(response_time, (int, float)):
                response_times.append(response_time)
        
        # Calculate percentiles
        if response_times:
            response_times.sort()
            p50 = self.percentile(response_times, 50)
            p90 = self.percentile(response_times, 90)
            p95 = self.percentile(response_times, 95)
            p99 = self.percentile(response_times, 99)
        else:
            p50 = 0
            p90 = 0
            p95 = 0
            p99 = 0
        
        return {
            "p50_response_time_ms": p50,
            "p90_response_time_ms": p90,
            "p95_response_time_ms": p95,
            "p99_response_time_ms": p99,
            "response_count": len(response_times)
        }
    
    def percentile(self, data: List[float], percentile: int) -> float:
        """Calculate the given percentile from a sorted list."""
        if not data:
            return 0
        
        index = (len(data) - 1) * percentile / 100.0
        if index.is_integer():
            return data[int(index)]
        else:
            lower_index = int(index)
            fraction = index - lower_index
            return data[lower_index] * (1 - fraction) + data[lower_index + 1] * fraction

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


class ResponseTimeTrendCalculator(BaseMetricCalculator):
    """Calculator for response time trends.
    
    Calculates how response times change over different time intervals.
    """
    
    def calculate(self, db: Session, start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None, 
                 agent_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 interval: str = 'hour',
                 **kwargs) -> Dict[str, Any]:
        """Calculate response time trend metrics.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            interval: Time interval for grouping ('hour', 'day', 'week')
            
        Returns:
            Dict containing response time trend metrics:
                - response_time_trends: Average response times grouped by time interval
                - interval: The time interval used for grouping
        """
        # Set default time range if not provided
        if not start_time:
            # Default time range based on interval
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
        elif interval == 'day':
            format_str = "%Y-%m-%d"
        else:  # 'week'
            format_str = "%Y-%W"  # Year and week number
            
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
        
        # Group response times by interval
        response_times_by_interval = {}
        
        for event in response_events:
            # Extract interval key
            interval_key = event.timestamp.strftime(format_str)
            
            # Initialize interval data if not exists
            if interval_key not in response_times_by_interval:
                response_times_by_interval[interval_key] = {
                    "response_times": [],
                    "count": 0
                }
            
            # Extract response time from event data
            response_time = None
            
            if event.data:
                if "duration_ms" in event.data:
                    response_time = event.data.get("duration_ms")
                elif "performance" in event.data and "duration_ms" in event.data.get("performance", {}):
                    response_time = event.data.get("performance", {}).get("duration_ms")
                elif "llm_output" in event.data and "usage" in event.data.get("llm_output", {}):
                    usage = event.data.get("llm_output", {}).get("usage", {})
                    if "response_time_ms" in usage:
                        response_time = usage.get("response_time_ms")
            
            # Add to interval data if valid
            if response_time is not None and isinstance(response_time, (int, float)):
                response_times_by_interval[interval_key]["response_times"].append(response_time)
                response_times_by_interval[interval_key]["count"] += 1
        
        # Calculate average response time for each interval
        response_time_trends = {}
        
        for interval_key, data in response_times_by_interval.items():
            if data["response_times"]:
                avg_time = statistics.mean(data["response_times"])
                min_time = min(data["response_times"])
                max_time = max(data["response_times"])
            else:
                avg_time = 0
                min_time = 0
                max_time = 0
                
            response_time_trends[interval_key] = {
                "average_response_time_ms": avg_time,
                "min_response_time_ms": min_time,
                "max_response_time_ms": max_time,
                "response_count": data["count"]
            }
        
        return {
            "response_time_trends": response_time_trends,
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


class RequestRateCalculator(BaseMetricCalculator):
    """Calculator for request rate metrics.
    
    Calculates the rate of requests over time.
    """
    
    def calculate(self, db: Session, start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None, 
                 agent_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 **kwargs) -> Dict[str, Any]:
        """Calculate request rate metrics.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            
        Returns:
            Dict containing request rate metrics:
                - requests_per_minute: Number of requests per minute
                - responses_per_minute: Number of responses per minute
                - time_range_minutes: Time range used for calculation in minutes
        """
        # Set default time range if not provided
        if not start_time:
            # Default to last hour
            start_time = datetime.utcnow() - timedelta(hours=1)
        
        if not end_time:
            end_time = datetime.utcnow()
        
        # Calculate time range in minutes
        time_range_minutes = (end_time - start_time).total_seconds() / 60
        
        # If time range is too small, default to 1 minute to avoid division by zero
        if time_range_minutes < 0.1:
            time_range_minutes = 1
        
        # Get request and response events
        request_events = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id,
            event_types=["model_request"],
            directions=["outgoing"]
        )
        
        response_events = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id,
            event_types=["model_response"],
            directions=["incoming"]
        )
        
        # Calculate rates
        requests_per_minute = len(request_events) / time_range_minutes
        responses_per_minute = len(response_events) / time_range_minutes
        
        return {
            "requests_per_minute": requests_per_minute,
            "responses_per_minute": responses_per_minute,
            "total_requests": len(request_events),
            "total_responses": len(response_events),
            "time_range_minutes": time_range_minutes
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


class RequestRateTrendCalculator(BaseMetricCalculator):
    """Calculator for request rate trends.
    
    Calculates how request rates change over different time intervals.
    """
    
    def calculate(self, db: Session, start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None, 
                 agent_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 interval: str = 'hour',
                 **kwargs) -> Dict[str, Any]:
        """Calculate request rate trend metrics.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            interval: Time interval for grouping ('hour', 'day', 'week')
            
        Returns:
            Dict containing request rate trend metrics:
                - request_rate_trends: Request rates grouped by time interval
                - interval: The time interval used for grouping
        """
        # Set default time range if not provided
        if not start_time:
            # Default time range based on interval
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
            delta_minutes = 60
        elif interval == 'day':
            format_str = "%Y-%m-%d"
            delta_minutes = 60 * 24
        else:  # 'week'
            format_str = "%Y-%W"  # Year and week number
            delta_minutes = 60 * 24 * 7
            
        # Get request and response events
        request_events = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id,
            event_types=["model_request"],
            directions=["outgoing"]
        )
        
        response_events = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id,
            event_types=["model_response"],
            directions=["incoming"]
        )
        
        # Group requests and responses by interval
        requests_by_interval = {}
        responses_by_interval = {}
        
        for event in request_events:
            interval_key = event.timestamp.strftime(format_str)
            if interval_key not in requests_by_interval:
                requests_by_interval[interval_key] = 0
            requests_by_interval[interval_key] += 1
            
        for event in response_events:
            interval_key = event.timestamp.strftime(format_str)
            if interval_key not in responses_by_interval:
                responses_by_interval[interval_key] = 0
            responses_by_interval[interval_key] += 1
        
        # Calculate rates for each interval
        request_rate_trends = {}
        
        # Get all interval keys from both requests and responses
        all_intervals = set(list(requests_by_interval.keys()) + list(responses_by_interval.keys()))
        
        for interval_key in all_intervals:
            request_count = requests_by_interval.get(interval_key, 0)
            response_count = responses_by_interval.get(interval_key, 0)
            
            request_rate_trends[interval_key] = {
                "requests_per_minute": request_count / delta_minutes,
                "responses_per_minute": response_count / delta_minutes,
                "total_requests": request_count,
                "total_responses": response_count
            }
        
        return {
            "request_rate_trends": request_rate_trends,
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


class ModelPerformanceCalculator(BaseMetricCalculator):
    """Calculator for model-specific performance metrics.
    
    Calculates performance metrics broken down by model.
    """
    
    def calculate(self, db: Session, start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None, 
                 agent_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 model_name: Optional[str] = None,
                 **kwargs) -> Dict[str, Any]:
        """Calculate model-specific performance metrics.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            model_name: Optional specific model to analyze
            
        Returns:
            Dict containing model performance metrics:
                - model_name: Name of the model (if specified)
                - performance_by_model: Performance metrics broken down by model
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
        
        # Group and analyze by model
        performance_by_model = {}
        
        for event in response_events:
            # Skip if no data
            if not event.data or not event.data.get("llm_output", {}):
                continue
            
            # Get model name
            response_model = event.data.get("llm_output", {}).get("model", "unknown")
            
            # Skip if not the requested model (when model_name is specified)
            if model_name and response_model != model_name:
                continue
            
            # Initialize model data if not exists
            if response_model not in performance_by_model:
                performance_by_model[response_model] = {
                    "response_times": [],
                    "response_count": 0,
                    "total_input_tokens": 0,
                    "total_output_tokens": 0
                }
            
            # Extract response time
            response_time = None
            
            if "duration_ms" in event.data:
                response_time = event.data.get("duration_ms")
            elif "performance" in event.data and "duration_ms" in event.data.get("performance", {}):
                response_time = event.data.get("performance", {}).get("duration_ms")
            elif "llm_output" in event.data and "usage" in event.data.get("llm_output", {}):
                usage = event.data.get("llm_output", {}).get("usage", {})
                if "response_time_ms" in usage:
                    response_time = usage.get("response_time_ms")
            
            # Add response time if valid
            if response_time is not None and isinstance(response_time, (int, float)):
                performance_by_model[response_model]["response_times"].append(response_time)
            
            # Increment response count
            performance_by_model[response_model]["response_count"] += 1
            
            # Extract token usage
            usage = event.data.get("llm_output", {}).get("usage", {})
            
            # Check different possible formats for token usage
            input_tokens = None
            output_tokens = None
            
            if usage:
                # Try to get input and output tokens
                if "input_tokens" in usage:
                    input_tokens = int(usage["input_tokens"])
                elif "prompt_tokens" in usage:
                    input_tokens = int(usage["prompt_tokens"])
                    
                if "output_tokens" in usage:
                    output_tokens = int(usage["output_tokens"])  
                elif "completion_tokens" in usage:
                    output_tokens = int(usage["completion_tokens"])
            
            # Alternative formats in response metadata
            if input_tokens is None or output_tokens is None:
                metadata = event.data.get("response", {}).get("message", {}).get("usage_metadata", {})
                if metadata:
                    if "input_tokens" in metadata and input_tokens is None:
                        input_tokens = int(metadata["input_tokens"])
                    if "output_tokens" in metadata and output_tokens is None:
                        output_tokens = int(metadata["output_tokens"])
            
            # Add token usage if valid
            if input_tokens is not None and isinstance(input_tokens, (int, float)):
                performance_by_model[response_model]["total_input_tokens"] += input_tokens
            
            if output_tokens is not None and isinstance(output_tokens, (int, float)):
                performance_by_model[response_model]["total_output_tokens"] += output_tokens
        
        # Calculate statistics for each model
        for model, data in performance_by_model.items():
            if data["response_times"]:
                data["average_response_time_ms"] = statistics.mean(data["response_times"])
                data["min_response_time_ms"] = min(data["response_times"])
                data["max_response_time_ms"] = max(data["response_times"])
                # Remove raw list to clean up the output
                del data["response_times"]
            else:
                data["average_response_time_ms"] = 0
                data["min_response_time_ms"] = 0
                data["max_response_time_ms"] = 0
                del data["response_times"]
        
        result = {
            "performance_by_model": performance_by_model
        }
        
        if model_name:
            result["model_name"] = model_name
            
        return result

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
metric_registry.register(ResponseTimeCalculator())
metric_registry.register(ResponseTimePercentileCalculator())
metric_registry.register(ResponseTimeTrendCalculator())
metric_registry.register(RequestRateCalculator())
metric_registry.register(RequestRateTrendCalculator())
metric_registry.register(ModelPerformanceCalculator()) 