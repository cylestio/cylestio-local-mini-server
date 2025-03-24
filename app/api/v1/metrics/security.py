from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from app.database.init_db import get_session
from app.business_logic.metrics.security_metrics import (
    SecurityAlertCountCalculator,
    AlertsBySeverityCalculator,
    AlertsByCategoryCalculator,
    SecurityAlertTrendCalculator
)
from app.business_logic.metrics.db_adapter import AsyncToSyncAdapter
from app.api.v1.metrics.utils import TimeRangeParams, format_response

router = APIRouter(prefix="/security", tags=["Security Metrics"])

@router.get("/alerts/count", response_model=Dict[str, Any])
async def get_security_alert_count(
    time_params: TimeRangeParams = Depends(),
    session: AsyncSession = Depends(get_session),
):
    """
    Get security alert count metrics.
    
    Returns the total number of security alerts and the alert rate.
    """
    calculator = AsyncToSyncAdapter(SecurityAlertCountCalculator())
    result = await calculator.calculate(
        db=session,
        start_time=time_params.start_time,
        end_time=time_params.end_time,
        agent_id=time_params.agent_id,
        session_id=time_params.session_id
    )
    
    return format_response(result, time_params.get_metadata())

@router.get("/risk_level", response_model=Dict[str, Any])
async def get_security_risk_level(
    time_params: TimeRangeParams = Depends(),
    session: AsyncSession = Depends(get_session),
):
    """
    Get security risk level metrics.
    
    Returns a breakdown of alerts by severity to determine risk level.
    """
    calculator = AsyncToSyncAdapter(AlertsBySeverityCalculator())
    result = await calculator.calculate(
        db=session,
        start_time=time_params.start_time,
        end_time=time_params.end_time,
        agent_id=time_params.agent_id,
        session_id=time_params.session_id
    )
    
    # Calculate an overall risk score based on severity distribution
    severity_weights = {
        "critical": 1.0,
        "high": 0.7,
        "medium": 0.4,
        "low": 0.1,
        "info": 0.0
    }
    
    total_alerts = sum(result["severity_distribution"].values())
    if total_alerts > 0:
        weighted_sum = sum(
            count * severity_weights.get(severity.lower(), 0) 
            for severity, count in result["severity_distribution"].items()
        )
        risk_score = (weighted_sum / total_alerts) * 100
    else:
        risk_score = 0
    
    # Add risk score to the result
    result["risk_score"] = round(risk_score, 2)
    
    # Map score to risk level
    if risk_score >= 70:
        risk_level = "Critical"
    elif risk_score >= 50:
        risk_level = "High"
    elif risk_score >= 30:
        risk_level = "Medium"
    elif risk_score > 0:
        risk_level = "Low"
    else:
        risk_level = "None"
        
    result["risk_level"] = risk_level
    
    return format_response(result, time_params.get_metadata())

@router.get("/alerts/by_category", response_model=Dict[str, Any])
async def get_alerts_by_category(
    time_params: TimeRangeParams = Depends(),
    session: AsyncSession = Depends(get_session),
):
    """
    Get security alerts breakdown by category.
    
    Returns the distribution of security alerts across different categories.
    """
    calculator = AsyncToSyncAdapter(AlertsByCategoryCalculator())
    result = await calculator.calculate(
        db=session,
        start_time=time_params.start_time,
        end_time=time_params.end_time,
        agent_id=time_params.agent_id,
        session_id=time_params.session_id
    )
    
    return format_response(result, time_params.get_metadata())

@router.get("/alerts/trend", response_model=Dict[str, Any])
async def get_security_alert_trend(
    time_params: TimeRangeParams = Depends(),
    interval: str = Query("hour", description="Time interval for trend data (minute, hour, day)"),
    session: AsyncSession = Depends(get_session),
):
    """
    Get security alert trend over time.
    
    Returns time series data for security alert metrics.
    """
    calculator = AsyncToSyncAdapter(SecurityAlertTrendCalculator())
    result = await calculator.calculate(
        db=session,
        start_time=time_params.start_time,
        end_time=time_params.end_time,
        agent_id=time_params.agent_id,
        session_id=time_params.session_id,
        interval=interval
    )
    
    metadata = time_params.get_metadata()
    metadata["interval"] = interval
    
    return format_response(result, metadata) 