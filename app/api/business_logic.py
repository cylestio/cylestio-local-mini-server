"""
API endpoints for the Business Logic Layer.

This module provides API endpoints for accessing metrics and insights from the business logic layer.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, UTC
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.business_logic import business_logic
from app.business_logic.base import BusinessLogicLayer

router = APIRouter()


@router.get("/available-metrics")
def get_available_metrics() -> Dict[str, List[str]]:
    """Get a list of all available metrics."""
    return {"metrics": sorted(BusinessLogicLayer.get_available_metrics())}


@router.get("/available-insights")
def get_available_insights() -> Dict[str, List[str]]:
    """Get a list of all available insights."""
    return {"insights": sorted(BusinessLogicLayer.get_available_insights())}


@router.get("/metrics")
def get_metrics(
    db: Session = Depends(get_db),
    metric_name: Optional[str] = Query(None, description="Name of the specific metric to calculate. If not provided, all metrics will be calculated."),
    start_time: Optional[datetime] = Query(None, description="Start time for events to consider (ISO format)"),
    end_time: Optional[datetime] = Query(None, description="End time for events to consider (ISO format)"),
    agent_id: Optional[str] = Query(None, description="Filter for a specific agent"),
    session_id: Optional[str] = Query(None, description="Filter for a specific session"),
    interval: Optional[str] = Query("hour", description="Time interval for trend metrics (hour, day, week)"),
    model_name: Optional[str] = Query(None, description="Filter for a specific model in model-specific metrics")
) -> Dict[str, Any]:
    """
    Calculate and return metrics.
    
    If metric_name is provided, only that specific metric will be calculated.
    Otherwise, all available metrics will be calculated.
    """
    bl = BusinessLogicLayer()
    
    # Set default time range if not provided
    if not start_time:
        start_time = datetime.now(UTC) - timedelta(days=1)
    if not end_time:
        end_time = datetime.now(UTC)
    
    # Check if the requested metric exists
    if metric_name and metric_name not in BusinessLogicLayer.get_available_metrics():
        raise HTTPException(status_code=404, detail=f"Metric '{metric_name}' not found")
    
    # Prepare parameters for metric calculation
    params = {
        "db": db,
        "start_time": start_time,
        "end_time": end_time,
        "agent_id": agent_id,
        "session_id": session_id,
        "interval": interval,
        "model_name": model_name
    }
    
    if metric_name:
        # Calculate just the requested metric
        try:
            result = bl.calculate_metric(metric_name, **params)
            return {metric_name: result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error calculating metric '{metric_name}': {str(e)}")
    else:
        # Calculate all metrics
        try:
            return bl.calculate_all_metrics(**params)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error calculating metrics: {str(e)}")


@router.get("/metrics/{metric_name}")
def get_specific_metric(
    metric_name: str,
    db: Session = Depends(get_db),
    start_time: Optional[datetime] = Query(None, description="Start time for events to consider (ISO format)"),
    end_time: Optional[datetime] = Query(None, description="End time for events to consider (ISO format)"),
    agent_id: Optional[str] = Query(None, description="Filter for a specific agent"),
    session_id: Optional[str] = Query(None, description="Filter for a specific session"),
    interval: Optional[str] = Query("hour", description="Time interval for trend metrics (hour, day, week)"),
    model_name: Optional[str] = Query(None, description="Filter for a specific model in model-specific metrics")
) -> Dict[str, Any]:
    """
    Calculate and return a specific metric.
    """
    bl = BusinessLogicLayer()
    
    # Set default time range if not provided
    if not start_time:
        start_time = datetime.now(UTC) - timedelta(days=1)
    if not end_time:
        end_time = datetime.now(UTC)
    
    # Check if the requested metric exists
    if metric_name not in BusinessLogicLayer.get_available_metrics():
        raise HTTPException(status_code=404, detail=f"Metric '{metric_name}' not found")
    
    # Prepare parameters for metric calculation
    params = {
        "db": db,
        "start_time": start_time,
        "end_time": end_time,
        "agent_id": agent_id,
        "session_id": session_id,
        "interval": interval,
        "model_name": model_name
    }
    
    try:
        result = bl.calculate_metric(metric_name, **params)
        return {metric_name: result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating metric '{metric_name}': {str(e)}")


@router.get("/insights")
def get_insights(
    db: Session = Depends(get_db),
    insight_name: Optional[str] = Query(None, description="Name of the specific insight to extract. If not provided, all insights will be extracted."),
    start_time: Optional[datetime] = Query(None, description="Start time for events to consider (ISO format)"),
    end_time: Optional[datetime] = Query(None, description="End time for events to consider (ISO format)"),
    agent_id: Optional[str] = Query(None, description="Filter for a specific agent"),
    session_id: Optional[str] = Query(None, description="Filter for a specific session")
) -> Dict[str, Any]:
    """
    Extract and return insights.
    
    If insight_name is provided, only that specific insight will be extracted.
    Otherwise, all available insights will be extracted.
    """
    bl = BusinessLogicLayer()
    
    # Set default time range if not provided
    if not start_time:
        start_time = datetime.now(UTC) - timedelta(days=7)
    if not end_time:
        end_time = datetime.now(UTC)
    
    # Check if the requested insight exists
    if insight_name and insight_name not in BusinessLogicLayer.get_available_insights():
        raise HTTPException(status_code=404, detail=f"Insight '{insight_name}' not found")
    
    # Prepare parameters for insight extraction
    params = {
        "db": db,
        "start_time": start_time,
        "end_time": end_time,
        "agent_id": agent_id,
        "session_id": session_id
    }
    
    if insight_name:
        # Extract just the requested insight
        try:
            result = bl.extract_insight(insight_name, **params)
            return {insight_name: result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error extracting insight '{insight_name}': {str(e)}")
    else:
        # Extract all insights
        try:
            return bl.extract_all_insights(**params)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error extracting insights: {str(e)}")


@router.get("/insights/{insight_name}")
def get_specific_insight(
    insight_name: str,
    db: Session = Depends(get_db),
    start_time: Optional[datetime] = Query(None, description="Start time for events to consider (ISO format)"),
    end_time: Optional[datetime] = Query(None, description="End time for events to consider (ISO format)"),
    agent_id: Optional[str] = Query(None, description="Filter for a specific agent"),
    session_id: Optional[str] = Query(None, description="Filter for a specific session")
) -> Dict[str, Any]:
    """
    Extract and return a specific insight.
    """
    bl = BusinessLogicLayer()
    
    # Set default time range if not provided
    if not start_time:
        start_time = datetime.now(UTC) - timedelta(days=7)
    if not end_time:
        end_time = datetime.now(UTC)
    
    # Check if the requested insight exists
    if insight_name not in BusinessLogicLayer.get_available_insights():
        raise HTTPException(status_code=404, detail=f"Insight '{insight_name}' not found")
    
    # Prepare parameters for insight extraction
    params = {
        "db": db,
        "start_time": start_time,
        "end_time": end_time,
        "agent_id": agent_id,
        "session_id": session_id
    }
    
    try:
        result = bl.extract_insight(insight_name, **params)
        return {insight_name: result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting insight '{insight_name}': {str(e)}")


@router.get("/metric-groups")
def get_metric_groups() -> Dict[str, Dict[str, List[str]]]:
    """
    Get metrics organized by functional groups.
    
    Returns metrics organized into logical groups for easier navigation.
    """
    # Define groups and the metrics that belong to them
    metric_groups = {
        "response_time": [
            "ResponseTimeCalculator",
            "ResponseTimePercentileCalculator",
            "ResponseTimeTrendCalculator",
            "ModelPerformanceCalculator"
        ],
        "request_rate": [
            "RequestRateCalculator",
            "RequestRateTrendCalculator"
        ],
        "token_usage": [
            "TotalTokenUsageCalculator",
            "AverageTokenUsageCalculator",
            "ModelTokenUsageCalculator",
            "TokenRateCalculator",
            "ModelTokenRateCalculator"
        ],
        "error_metrics": [
            "ErrorRateCalculator",
            "ErrorTrendCalculator",
            "ErrorPatternCalculator",
            "ErrorTypeCalculator",
            "ErrorSeverityDistributionCalculator"
        ],
        "security_metrics": [
            "SecurityAlertCountCalculator",
            "AlertsBySeverityCalculator",
            "AlertsByCategoryCalculator",
            "AlertsByAgentCalculator",
            "SecurityAlertTrendCalculator"
        ]
    }
    
    return {"metric_groups": metric_groups}


@router.get("/insight-groups")
def get_insight_groups() -> Dict[str, Dict[str, List[str]]]:
    """
    Get insights organized by functional groups.
    
    Returns insights organized into logical groups for easier navigation.
    """
    # Define groups and the insights that belong to them
    insight_groups = {
        "agent_insights": [
            "AgentHealthInsightExtractor",
            "AgentActivityInsightExtractor"
        ],
        "conversation_insights": [
            "ConversationQualityInsightExtractor",
            "ResponseTimeInsightExtractor",
            "ContentQualityInsightExtractor"
        ],
        "session_insights": [
            "SessionAnalyticsInsightExtractor",
            "UserEngagementInsightExtractor"
        ],
        "content_insights": [
            "ContentAnalyticsInsightExtractor",
            "TopicAnalyticsInsightExtractor"
        ]
    }
    
    return {"insight_groups": insight_groups} 