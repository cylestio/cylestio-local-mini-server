"""
Token Usage Metrics module.

This module provides metric calculators for token usage and related metrics.
Each calculator focuses on a specific metric for better modularity.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import statistics
from sqlalchemy.orm import Session

from app.business_logic.metrics.base import BaseMetricCalculator, metric_registry
from app.models.event import Event


class TotalTokenUsageCalculator(BaseMetricCalculator):
    """Calculator for total token usage.
    
    Calculates total tokens used across all requests/responses.
    """
    
    def calculate(self, db: Session, start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None, 
                 agent_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 **kwargs) -> Dict[str, Any]:
        """Calculate total token usage metric.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            
        Returns:
            Dict containing total token usage:
                - total_input_tokens: Total input tokens used
                - total_output_tokens: Total output tokens used
                - total_tokens: Total tokens used (input + output)
                - event_count: Number of events analyzed
        """
        # Get model responses (which contain token usage info)
        model_responses = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id,
            event_types=["model_response"],
            directions=["incoming"]
        )
        
        # Extract token usage data
        total_input_tokens = 0
        total_output_tokens = 0
        events_with_token_data = 0
        
        for response in model_responses:
            if not response.data or not response.data.get("llm_output", {}):
                continue
                
            # Get token usage
            usage = response.data.get("llm_output", {}).get("usage", {})
            
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
                metadata = response.data.get("response", {}).get("message", {}).get("usage_metadata", {})
                if metadata:
                    if "input_tokens" in metadata and input_tokens is None:
                        input_tokens = int(metadata["input_tokens"])
                    if "output_tokens" in metadata and output_tokens is None:
                        output_tokens = int(metadata["output_tokens"])
            
            # Skip if we couldn't find token usage
            if input_tokens is None or output_tokens is None:
                continue
                
            # Accumulate totals
            total_input_tokens += input_tokens
            total_output_tokens += output_tokens
            events_with_token_data += 1
        
        # Calculate total tokens
        total_tokens = total_input_tokens + total_output_tokens
        
        return {
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_tokens": total_tokens,
            "event_count": len(model_responses),
            "events_with_token_data": events_with_token_data
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


class AverageTokenUsageCalculator(BaseMetricCalculator):
    """Calculator for average token usage.
    
    Calculates average tokens used per request/response.
    """
    
    def calculate(self, db: Session, start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None, 
                 agent_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 **kwargs) -> Dict[str, Any]:
        """Calculate average token usage metric.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            
        Returns:
            Dict containing average token usage:
                - average_input_tokens_per_request: Average input tokens per request
                - average_output_tokens_per_response: Average output tokens per response
                - events_analyzed: Number of events analyzed
        """
        # Get model responses (which contain token usage info)
        model_responses = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id,
            event_types=["model_response"],
            directions=["incoming"]
        )
        
        # Extract token usage data
        input_tokens_list = []
        output_tokens_list = []
        
        for response in model_responses:
            if not response.data or not response.data.get("llm_output", {}):
                continue
                
            # Get token usage
            usage = response.data.get("llm_output", {}).get("usage", {})
            
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
                metadata = response.data.get("response", {}).get("message", {}).get("usage_metadata", {})
                if metadata:
                    if "input_tokens" in metadata and input_tokens is None:
                        input_tokens = int(metadata["input_tokens"])
                    if "output_tokens" in metadata and output_tokens is None:
                        output_tokens = int(metadata["output_tokens"])
            
            # Skip if we couldn't find token usage
            if input_tokens is None or output_tokens is None:
                continue
                
            # Add to lists for average calculation
            input_tokens_list.append(input_tokens)
            output_tokens_list.append(output_tokens)
        
        # Calculate averages
        average_input_tokens = statistics.mean(input_tokens_list) if input_tokens_list else 0
        average_output_tokens = statistics.mean(output_tokens_list) if output_tokens_list else 0
        
        return {
            "average_input_tokens_per_request": average_input_tokens,
            "average_output_tokens_per_response": average_output_tokens,
            "events_analyzed": len(model_responses),
            "events_with_token_data": len(input_tokens_list)
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


class ModelTokenUsageCalculator(BaseMetricCalculator):
    """Calculator for model-specific token usage.
    
    Calculates token usage broken down by model.
    """
    
    def calculate(self, db: Session, start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None, 
                 agent_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 model_name: Optional[str] = None,
                 **kwargs) -> Dict[str, Any]:
        """Calculate model-specific token usage metric.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            model_name: Optional specific model to analyze
            
        Returns:
            Dict containing model token usage:
                - model_name: Name of the model (if specified)
                - token_usage_by_model: Token usage broken down by model
        """
        # Get model responses (which contain token usage info)
        model_responses = self.get_filtered_events(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id,
            event_types=["model_response"],
            directions=["incoming"]
        )
        
        # Extract token usage by model
        token_usage_by_model = {}
        
        for response in model_responses:
            if not response.data or not response.data.get("llm_output", {}):
                continue
                
            # Get model info
            response_model = response.data.get("llm_output", {}).get("model", "unknown")
            
            # Skip if not the requested model (when model_name is specified)
            if model_name and response_model != model_name:
                continue
            
            # Get token usage
            usage = response.data.get("llm_output", {}).get("usage", {})
            
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
                metadata = response.data.get("response", {}).get("message", {}).get("usage_metadata", {})
                if metadata:
                    if "input_tokens" in metadata and input_tokens is None:
                        input_tokens = int(metadata["input_tokens"])
                    if "output_tokens" in metadata and output_tokens is None:
                        output_tokens = int(metadata["output_tokens"])
            
            # Skip if we couldn't find token usage
            if input_tokens is None or output_tokens is None:
                continue
            
            # Initialize model data if not exists
            if response_model not in token_usage_by_model:
                token_usage_by_model[response_model] = {
                    "total_input_tokens": 0,
                    "total_output_tokens": 0,
                    "total_tokens": 0,
                    "request_count": 0,
                    "input_tokens_list": [],
                    "output_tokens_list": []
                }
            
            # Update model data
            token_usage_by_model[response_model]["total_input_tokens"] += input_tokens
            token_usage_by_model[response_model]["total_output_tokens"] += output_tokens
            token_usage_by_model[response_model]["total_tokens"] += input_tokens + output_tokens
            token_usage_by_model[response_model]["request_count"] += 1
            token_usage_by_model[response_model]["input_tokens_list"].append(input_tokens)
            token_usage_by_model[response_model]["output_tokens_list"].append(output_tokens)
        
        # Calculate model-specific averages
        for model, data in token_usage_by_model.items():
            if data["input_tokens_list"]:
                data["average_input_tokens"] = statistics.mean(data["input_tokens_list"])
            else:
                data["average_input_tokens"] = 0
                
            if data["output_tokens_list"]:
                data["average_output_tokens"] = statistics.mean(data["output_tokens_list"])
            else:
                data["average_output_tokens"] = 0
                
            # Remove lists to clean up the output
            del data["input_tokens_list"]
            del data["output_tokens_list"]
        
        result = {
            "token_usage_by_model": token_usage_by_model
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


class TokenRateCalculator(BaseMetricCalculator):
    """Calculator for token usage rate.
    
    Calculates the rate of token usage over time.
    """
    
    def calculate(self, db: Session, start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None, 
                 agent_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 **kwargs) -> Dict[str, Any]:
        """Calculate token rate metric.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            
        Returns:
            Dict containing token rate metrics:
                - tokens_per_minute: Token usage rate per minute
                - input_tokens_per_minute: Input token usage rate per minute
                - output_tokens_per_minute: Output token usage rate per minute
                - time_range_minutes: Time range used for calculation in minutes
        """
        # Get time range
        if not start_time:
            # Default to last hour if no start time
            start_time = datetime.utcnow() - timedelta(hours=1)
        
        if not end_time:
            end_time = datetime.utcnow()
        
        # Calculate time range in minutes
        time_range_minutes = (end_time - start_time).total_seconds() / 60
        
        # If time range is too small, default to 1 minute to avoid division by zero
        if time_range_minutes < 0.1:
            time_range_minutes = 1
        
        # Get total token usage
        total_usage = TotalTokenUsageCalculator().calculate(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id
        )
        
        total_input_tokens = total_usage.get("total_input_tokens", 0)
        total_output_tokens = total_usage.get("total_output_tokens", 0)
        total_tokens = total_usage.get("total_tokens", 0)
        
        # Calculate rates
        tokens_per_minute = total_tokens / time_range_minutes
        input_tokens_per_minute = total_input_tokens / time_range_minutes
        output_tokens_per_minute = total_output_tokens / time_range_minutes
        
        return {
            "tokens_per_minute": tokens_per_minute,
            "input_tokens_per_minute": input_tokens_per_minute,
            "output_tokens_per_minute": output_tokens_per_minute,
            "total_tokens": total_tokens,
            "time_range_minutes": time_range_minutes
        }


class ModelTokenRateCalculator(BaseMetricCalculator):
    """Calculator for model-specific token usage rate.
    
    Calculates token usage rates broken down by model.
    """
    
    def calculate(self, db: Session, start_time: Optional[datetime] = None, 
                 end_time: Optional[datetime] = None, 
                 agent_id: Optional[str] = None,
                 session_id: Optional[str] = None,
                 model_name: Optional[str] = None,
                 **kwargs) -> Dict[str, Any]:
        """Calculate model-specific token rate metrics.
        
        Args:
            db: Database session
            start_time: Start time for events to consider
            end_time: End time for events to consider
            agent_id: Optional filter for specific agent
            session_id: Optional filter for specific session
            model_name: Optional specific model to analyze
            
        Returns:
            Dict containing model token rates:
                - model_name: Name of the model (if specified)
                - token_rates_by_model: Token rates broken down by model
                - time_range_minutes: Time range used for calculation in minutes
        """
        # Get time range
        if not start_time:
            # Default to last hour if no start time
            start_time = datetime.utcnow() - timedelta(hours=1)
        
        if not end_time:
            end_time = datetime.utcnow()
        
        # Calculate time range in minutes
        time_range_minutes = (end_time - start_time).total_seconds() / 60
        
        # If time range is too small, default to 1 minute to avoid division by zero
        if time_range_minutes < 0.1:
            time_range_minutes = 1
        
        # Get model token usage
        model_usage = ModelTokenUsageCalculator().calculate(
            db=db,
            start_time=start_time,
            end_time=end_time,
            agent_id=agent_id,
            session_id=session_id,
            model_name=model_name
        )
        
        token_usage_by_model = model_usage.get("token_usage_by_model", {})
        
        # Calculate rates for each model
        token_rates_by_model = {}
        
        for model, usage in token_usage_by_model.items():
            token_rates_by_model[model] = {
                "tokens_per_minute": usage.get("total_tokens", 0) / time_range_minutes,
                "input_tokens_per_minute": usage.get("total_input_tokens", 0) / time_range_minutes,
                "output_tokens_per_minute": usage.get("total_output_tokens", 0) / time_range_minutes,
                "total_tokens": usage.get("total_tokens", 0),
                "total_input_tokens": usage.get("total_input_tokens", 0),
                "total_output_tokens": usage.get("total_output_tokens", 0),
                "request_count": usage.get("request_count", 0)
            }
        
        result = {
            "token_rates_by_model": token_rates_by_model,
            "time_range_minutes": time_range_minutes
        }
        
        if model_name:
            result["model_name"] = model_name
            
        return result


# Register the metric calculators
metric_registry.register(TotalTokenUsageCalculator())
metric_registry.register(AverageTokenUsageCalculator())
metric_registry.register(ModelTokenUsageCalculator())
metric_registry.register(TokenRateCalculator())
metric_registry.register(ModelTokenRateCalculator()) 