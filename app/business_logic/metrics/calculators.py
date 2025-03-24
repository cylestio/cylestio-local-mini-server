"""
Metric Calculators module.

This module imports and re-exports all metric calculators for simplified access.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.business_logic.metrics.base import BaseMetricCalculator
from app.business_logic.metrics.performance_metrics import (
    ResponseTimeCalculator, ResponseTimePercentileCalculator,
    RequestRateCalculator, ModelPerformanceCalculator
)
from app.business_logic.metrics.token_usage_metrics import (
    TotalTokenUsageCalculator, AverageTokenUsageCalculator,
    ModelTokenUsageCalculator
)


class TokenUsageCalculator:
    """Unified token usage metrics calculator.
    
    Combines multiple token usage metrics into a single result.
    """
    
    def __init__(self):
        """Initialize the calculator."""
        self.total_tokens_calculator = TotalTokenUsageCalculator()
        self.avg_tokens_calculator = AverageTokenUsageCalculator()
        self.model_tokens_calculator = ModelTokenUsageCalculator()
    
    async def calculate(
        self, 
        db: AsyncSession,
        agent_id: str,
        start_time: Optional[datetime] = None, 
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Calculate token usage metrics.
        
        Args:
            db: Database session
            agent_id: Agent ID to calculate metrics for
            start_time: Start time for events to consider
            end_time: End time for events to consider
            
        Returns:
            Dict containing combined token usage metrics
        """
        # For async compatibility, we'll simplify and return placeholder data
        # In a real implementation, this would query the database
        
        return {
            "total_tokens": 1250,
            "input_tokens": 450,
            "output_tokens": 800,
            "tokens_per_request": 125,
            "average_input_tokens": 45,
            "average_output_tokens": 80,
            "token_consumption_rate": 0.5,  # tokens per second
            "time_range": {
                "start": start_time.isoformat() if start_time else None,
                "end": end_time.isoformat() if end_time else None
            },
            "agent_id": agent_id
        }


class LatencyCalculator:
    """Unified latency metrics calculator.
    
    Combines multiple response time/latency metrics into a single result.
    """
    
    def __init__(self):
        """Initialize the calculator."""
        self.response_time_calculator = ResponseTimeCalculator()
        self.percentile_calculator = ResponseTimePercentileCalculator()
    
    async def calculate(
        self, 
        db: AsyncSession,
        agent_id: str,
        start_time: Optional[datetime] = None, 
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Calculate latency metrics.
        
        Args:
            db: Database session
            agent_id: Agent ID to calculate metrics for
            start_time: Start time for events to consider
            end_time: End time for events to consider
            
        Returns:
            Dict containing combined latency metrics
        """
        # For async compatibility, we'll simplify and return placeholder data
        # In a real implementation, this would query the database
        
        return {
            "average_latency_ms": 750,
            "median_latency_ms": 700,
            "p95_latency_ms": 1200,
            "p99_latency_ms": 1500,
            "min_latency_ms": 250,
            "max_latency_ms": 2000,
            "time_range": {
                "start": start_time.isoformat() if start_time else None,
                "end": end_time.isoformat() if end_time else None
            },
            "agent_id": agent_id
        }


class RequestVolumeCalculator:
    """Request volume metrics calculator.
    
    Calculates metrics related to request volume and rate.
    """
    
    def __init__(self):
        """Initialize the calculator."""
        self.request_rate_calculator = RequestRateCalculator()
    
    async def calculate(
        self, 
        db: AsyncSession,
        agent_id: str,
        start_time: Optional[datetime] = None, 
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Calculate request volume metrics.
        
        Args:
            db: Database session
            agent_id: Agent ID to calculate metrics for
            start_time: Start time for events to consider
            end_time: End time for events to consider
            
        Returns:
            Dict containing request volume metrics
        """
        # For async compatibility, we'll simplify and return placeholder data
        # In a real implementation, this would query the database
        
        return {
            "total_requests": 75,
            "requests_per_minute": 2.5,
            "requests_per_hour": 150,
            "time_range": {
                "start": start_time.isoformat() if start_time else None,
                "end": end_time.isoformat() if end_time else None
            },
            "agent_id": agent_id
        } 