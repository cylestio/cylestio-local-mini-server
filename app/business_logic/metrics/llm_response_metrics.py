"""
LLM Response Metrics module.

This module provides metric calculators for LLM response times and related metrics.
Each calculator focuses on a specific metric for better modularity.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import statistics
from sqlalchemy.orm import Session

from app.business_logic.metrics.base import BaseMetricCalculator, metric_registry
from app.models.event import Event


class AverageResponseTimeCalculator(BaseMetricCalculator):
    """Calculator for average LLM response time.
    
    Calculates the average response time for LLM calls.
    """
    
    def calculate(self, db: Session, start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None, 
                 agent_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 **kwargs) -> Dict[str, Any]:
        """Calculate average response time metric.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            
        Returns:
            Dict containing average response time:
                - average_response_time_ms: Average response time in milliseconds
                - total_responses: Total number of responses considered
        """
        # Get model responses
        model_responses = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id,
            event_types=["model_response"],
            directions=["incoming"]
        )
        
        # Extract response times from events
        response_times = []
        
        for response in model_responses:
            if not response.data or not response.data.get("performance", {}).get("duration_ms"):
                continue
                
            # Get response time
            duration_ms = float(response.data["performance"]["duration_ms"])
            response_times.append(duration_ms)
        
        # Calculate statistics
        result = {
            "total_responses": len(model_responses),
            "responses_with_duration": len(response_times)
        }
        
        # Add overall statistics if we have response times
        if response_times:
            result.update({
                "average_response_time_ms": statistics.mean(response_times)
            })
        else:
            result.update({
                "average_response_time_ms": None
            })
        
        return result
    
    def get_filtered_events(self, db: Session, start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None,
                           agent_id: Optional[str] = None,
                           session_id: Optional[str] = None,
                           event_types: Optional[List[str]] = None,
                           channels: Optional[List[str]] = None,
                           levels: Optional[List[str]] = None,
                           directions: Optional[List[str]] = None) -> List[Event]:
        """Get filtered events based on parameters with direction filter.
        
        Extends the base method to add filtering by direction.
        """
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
    
    Calculates response time percentiles for LLM calls.
    """
    
    def calculate(self, db: Session, start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None, 
                 agent_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 percentile: int = 95,
                 **kwargs) -> Dict[str, Any]:
        """Calculate response time percentile metric.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            percentile: Percentile to calculate (default: 95)
            
        Returns:
            Dict containing percentile response time:
                - percentile: The percentile that was calculated
                - percentile_response_time_ms: The response time at the specified percentile
                - total_responses: Total number of responses considered
        """
        # Get model responses
        model_responses = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id,
            event_types=["model_response"],
            directions=["incoming"]
        )
        
        # Extract response times from events
        response_times = []
        
        for response in model_responses:
            if not response.data or not response.data.get("performance", {}).get("duration_ms"):
                continue
                
            # Get response time
            duration_ms = float(response.data["performance"]["duration_ms"])
            response_times.append(duration_ms)
        
        # Calculate percentile
        result = {
            "percentile": percentile,
            "total_responses": len(model_responses),
            "responses_with_duration": len(response_times)
        }
        
        if response_times:
            result["percentile_response_time_ms"] = self._calculate_percentile(response_times, percentile)
        else:
            result["percentile_response_time_ms"] = None
        
        return result
    
    def _calculate_percentile(self, data: List[float], percentile: int) -> float:
        """Calculate the specified percentile of the data."""
        if not data:
            return 0
            
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * percentile / 100
        f = int(k)
        c = k - f
        
        if f + 1 < len(sorted_data):
            return sorted_data[f] * (1 - c) + sorted_data[f + 1] * c
        else:
            return sorted_data[f]
    
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


class ModelResponseTimeCalculator(BaseMetricCalculator):
    """Calculator for model-specific response times.
    
    Calculates response times broken down by model.
    """
    
    def calculate(self, db: Session, start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None, 
                 agent_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 model_name: Optional[str] = None,
                 **kwargs) -> Dict[str, Any]:
        """Calculate model-specific response time metrics.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            model_name: Optional specific model to analyze
            
        Returns:
            Dict containing model response times:
                - model_name: Name of the model (if specified)
                - response_times_by_model: Response times broken down by model
        """
        # Get model responses
        model_responses = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id,
            event_types=["model_response"],
            directions=["incoming"]
        )
        
        # Extract response times by model
        model_response_times = {}
        
        for response in model_responses:
            if not response.data or not response.data.get("performance", {}).get("duration_ms"):
                continue
                
            # Get response time
            duration_ms = float(response.data["performance"]["duration_ms"])
            
            # Get model info
            response_model = response.data.get("llm_output", {}).get("model", "unknown")
            
            # Skip if not the requested model (when model_name is specified)
            if model_name and response_model != model_name:
                continue
            
            if response_model not in model_response_times:
                model_response_times[response_model] = []
            model_response_times[response_model].append(duration_ms)
        
        # Calculate statistics for each model
        result = {
            "response_times_by_model": {}
        }
        
        if model_name:
            result["model_name"] = model_name
        
        for model, times in model_response_times.items():
            if times:
                result["response_times_by_model"][model] = {
                    "average_response_time_ms": statistics.mean(times),
                    "median_response_time_ms": statistics.median(times),
                    "min_response_time_ms": min(times),
                    "max_response_time_ms": max(times), 
                    "p95_response_time_ms": self._calculate_percentile(times, 95),
                    "p99_response_time_ms": self._calculate_percentile(times, 99),
                    "total_requests": len(times)
                }
        
        return result
    
    def _calculate_percentile(self, data: List[float], percentile: int) -> float:
        """Calculate the specified percentile of the data."""
        if not data:
            return 0
            
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * percentile / 100
        f = int(k)
        c = k - f
        
        if f + 1 < len(sorted_data):
            return sorted_data[f] * (1 - c) + sorted_data[f + 1] * c
        else:
            return sorted_data[f]
    
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


class RequestCountCalculator(BaseMetricCalculator):
    """Calculator for LLM request counts.
    
    Calculates the number of LLM requests.
    """
    
    def calculate(self, db: Session, start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None, 
                 agent_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 **kwargs) -> Dict[str, Any]:
        """Calculate request count metrics.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            
        Returns:
            Dict containing request counts:
                - total_requests: Total number of requests
        """
        # Get model requests
        requests = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id,
            event_types=["model_request"],
            directions=["outgoing"]
        )
        
        return {
            "total_requests": len(requests)
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


class SuccessRateCalculator(BaseMetricCalculator):
    """Calculator for LLM success rate.
    
    Calculates the percentage of requests that received successful responses.
    """
    
    def calculate(self, db: Session, start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None, 
                 agent_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 **kwargs) -> Dict[str, Any]:
        """Calculate success rate metrics.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            
        Returns:
            Dict containing success rate metrics:
                - total_requests: Total number of requests
                - total_responses: Total number of responses
                - success_rate: Percentage of requests that received responses
        """
        # Get model requests and responses
        requests = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id,
            event_types=["model_request"],
            directions=["outgoing"]
        )
        
        responses = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id,
            event_types=["model_response"],
            directions=["incoming"]
        )
        
        # Calculate success rate
        total_requests = len(requests)
        total_responses = len(responses)
        success_rate = (total_responses / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "total_requests": total_requests,
            "total_responses": total_responses,
            "success_rate": success_rate
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
metric_registry.register(AverageResponseTimeCalculator())
metric_registry.register(ResponseTimePercentileCalculator())
metric_registry.register(ModelResponseTimeCalculator())
metric_registry.register(RequestCountCalculator())
metric_registry.register(SuccessRateCalculator()) 