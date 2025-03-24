from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from app.database.init_db import get_session
from app.business_logic.metrics.usage_metrics import (
    AgentUsageCalculator,
    FrameworkUsageCalculator,
    EventTypeDistributionCalculator,
    SessionCountCalculator
)
from app.business_logic.metrics.db_adapter import AsyncToSyncAdapter
from app.api.v1.metrics.utils import TimeRangeParams, format_response

router = APIRouter(prefix="/usage", tags=["Usage Metrics"])

@router.get("/requests/by_agent", response_model=Dict[str, Any])
async def get_requests_by_agent(
    time_params: TimeRangeParams = Depends(),
    top_n: int = Query(10, description="Number of top agents to include"),
    session: AsyncSession = Depends(get_session),
):
    """
    Get request count breakdown by agent.
    
    Returns the distribution of requests across different agents.
    """
    calculator = AsyncToSyncAdapter(AgentUsageCalculator())
    result = await calculator.calculate(
        db=session,
        start_time=time_params.start_time,
        end_time=time_params.end_time,
        top_n=top_n
    )
    
    metadata = time_params.get_metadata()
    metadata["top_n"] = top_n
    
    return format_response(result, metadata)

@router.get("/frameworks/distribution", response_model=Dict[str, Any])
async def get_frameworks_distribution(
    time_params: TimeRangeParams = Depends(),
    top_n: int = Query(10, description="Number of top frameworks to include"),
    session: AsyncSession = Depends(get_session),
):
    """
    Get framework usage distribution.
    
    Returns the breakdown of usage across different frameworks.
    """
    calculator = AsyncToSyncAdapter(FrameworkUsageCalculator())
    result = await calculator.calculate(
        db=session,
        start_time=time_params.start_time,
        end_time=time_params.end_time,
        agent_id=time_params.agent_id,
        session_id=time_params.session_id,
        top_n=top_n
    )
    
    metadata = time_params.get_metadata()
    metadata["top_n"] = top_n
    
    return format_response(result, metadata)

@router.get("/events/distribution", response_model=Dict[str, Any])
async def get_event_type_distribution(
    time_params: TimeRangeParams = Depends(),
    top_n: int = Query(10, description="Number of top event types to include"),
    session: AsyncSession = Depends(get_session),
):
    """
    Get event type distribution.
    
    Returns the breakdown of events by type.
    """
    calculator = AsyncToSyncAdapter(EventTypeDistributionCalculator())
    result = await calculator.calculate(
        db=session,
        start_time=time_params.start_time,
        end_time=time_params.end_time,
        agent_id=time_params.agent_id,
        session_id=time_params.session_id,
        top_n=top_n
    )
    
    metadata = time_params.get_metadata()
    metadata["top_n"] = top_n
    
    return format_response(result, metadata)

@router.get("/sessions/count", response_model=Dict[str, Any])
async def get_session_count(
    time_params: TimeRangeParams = Depends(),
    session: AsyncSession = Depends(get_session),
):
    """
    Get session count metrics.
    
    Returns the number of unique sessions in the specified time period.
    """
    calculator = AsyncToSyncAdapter(SessionCountCalculator())
    result = await calculator.calculate(
        db=session,
        start_time=time_params.start_time,
        end_time=time_params.end_time,
        agent_id=time_params.agent_id
    )
    
    return format_response(result, time_params.get_metadata()) 