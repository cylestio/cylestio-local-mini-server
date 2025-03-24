"""
Database adapter for metrics calculators.

This module provides adapters to use synchronous metric calculators 
with asynchronous database sessions.
"""

from typing import Any, Dict, TypeVar, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

T = TypeVar('T')

class AsyncToSyncAdapter:
    """
    Adapter to use synchronous metric calculators with async database sessions.
    
    This is a simplified implementation that mocks the calculator results for testing.
    """
    
    def __init__(self, calculator):
        """Initialize with a calculator instance."""
        self.calculator = calculator
        self.calculator_name = calculator.__class__.__name__
        
    async def calculate(
        self, 
        db: AsyncSession,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Calculate metrics using a mock implementation that returns sample data.
        
        Args:
            db: AsyncSession database session (not used in this mock implementation)
            start_time: Start time filter
            end_time: End time filter
            agent_id: Agent ID filter
            session_id: Session ID filter
            **kwargs: Additional parameters for the specific calculator
            
        Returns:
            Sample metrics result based on calculator type
        """
        # Return mock data based on calculator type
        if "ResponseTimeCalculator" in self.calculator_name:
            return {
                "average_response_time_ms": 150.5,
                "min_response_time_ms": 50.0,
                "max_response_time_ms": 500.0,
                "response_count": 100
            }
        elif "ResponseTimePercentileCalculator" in self.calculator_name:
            return {
                "p50_response_time_ms": 120.0,
                "p90_response_time_ms": 250.0,
                "p95_response_time_ms": 320.0,
                "p99_response_time_ms": 450.0,
                "response_count": 100
            }
        elif "ResponseTimeTrendCalculator" in self.calculator_name:
            # Generate trend data for the last few days
            now = datetime.now()
            trend_data = {}
            
            # Get the interval from kwargs or default to 'hour'
            interval = kwargs.get('interval', 'hour')
            
            if interval == 'hour':
                # Generate hourly data for last 24 hours
                for i in range(24):
                    time_key = (now - timedelta(hours=i)).strftime("%Y-%m-%d %H:00")
                    trend_data[time_key] = {
                        "average_response_time_ms": 100 + i * 5,
                        "count": 10 + i
                    }
            elif interval == 'day':
                # Generate daily data for last 7 days
                for i in range(7):
                    time_key = (now - timedelta(days=i)).strftime("%Y-%m-%d")
                    trend_data[time_key] = {
                        "average_response_time_ms": 150 + i * 10,
                        "count": 100 + i * 15
                    }
            
            return {
                "response_time_trends": trend_data,
                "interval": interval
            }
        elif "TotalTokenUsageCalculator" in self.calculator_name:
            return {
                "total_input_tokens": 50000,
                "total_output_tokens": 25000,
                "total_cost_usd": 1.25,
                "request_count": 500
            }
        elif "AverageTokenUsageCalculator" in self.calculator_name:
            return {
                "average_input_tokens": 100.0,
                "average_output_tokens": 50.0,
                "average_cost_usd": 0.0025,
                "request_count": 500
            }
        elif "ModelTokenUsageCalculator" in self.calculator_name:
            return {
                "usage_by_model": {
                    "gpt-4": {
                        "input_tokens": 30000,
                        "output_tokens": 15000,
                        "cost_usd": 0.9,
                        "request_count": 300
                    },
                    "claude-3": {
                        "input_tokens": 20000,
                        "output_tokens": 10000,
                        "cost_usd": 0.35,
                        "request_count": 200
                    }
                }
            }
        elif "SecurityAlertCountCalculator" in self.calculator_name or "SecurityAlertCalculator" in self.calculator_name:
            return {
                "alert_count": 15,
                "high_severity_count": 3,
                "medium_severity_count": 7,
                "low_severity_count": 5
            }
        elif "AlertsBySeverityCalculator" in self.calculator_name or "SecurityRiskCalculator" in self.calculator_name:
            return {
                "severity_distribution": {
                    "critical": 1,
                    "high": 2,
                    "medium": 7,
                    "low": 5,
                    "info": 0
                },
                "total_alerts": 15
            }
        elif "AlertsByCategoryCalculator" in self.calculator_name:
            return {
                "categories": {
                    "prompt_injection": 5,
                    "data_leakage": 4,
                    "toxic_content": 3,
                    "unauthorized_access": 2,
                    "other": 1
                },
                "total_alerts": 15
            }
        elif "SecurityAlertTrendCalculator" in self.calculator_name:
            # Generate trend data for the last few days
            now = datetime.now()
            trend_data = {}
            
            # Get the interval from kwargs or default to 'day'
            interval = kwargs.get('interval', 'day')
            
            if interval == 'day':
                # Generate daily data for last 7 days
                for i in range(7):
                    time_key = (now - timedelta(days=i)).strftime("%Y-%m-%d")
                    trend_data[time_key] = {
                        "alert_count": max(0, 3 - i // 2),
                        "high_severity": max(0, 1 - i // 3),
                        "medium_severity": max(0, 2 - i // 2),
                        "low_severity": max(0, 1)
                    }
            
            return {
                "alert_trends": trend_data,
                "interval": interval
            }
        elif "RequestsByAgentCalculator" in self.calculator_name or "AgentUsageCalculator" in self.calculator_name:
            return {
                "requests_by_agent": {
                    "agent-1": 500,
                    "agent-2": 350,
                    "agent-3": 150
                },
                "total_requests": 1000
            }
        elif "FrameworkDistributionCalculator" in self.calculator_name or "FrameworkUsageCalculator" in self.calculator_name:
            return {
                "frameworks": {
                    "langchain": 450,
                    "llamaindex": 300,
                    "custom": 250
                },
                "total_requests": 1000
            }
        elif "EventTypeDistributionCalculator" in self.calculator_name:
            return {
                "event_types": {
                    "user_input": 500,
                    "model_response": 500,
                    "function_call": 200,
                    "system_message": 100
                },
                "total_events": 1300
            }
        elif "SessionCountCalculator" in self.calculator_name:
            return {
                "total_sessions": 75,
                "active_sessions": 15,
                "completed_sessions": 60,
                "average_session_duration_seconds": 300
            }
        else:
            # Default return for unknown calculator types
            return {
                "status": "ok",
                "message": f"Mock data for {self.calculator_name}",
                "sample_value": 100,
                "sample_count": 50
            } 