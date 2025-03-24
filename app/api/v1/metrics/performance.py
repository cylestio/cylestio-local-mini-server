from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from app.database.init_db import get_session
from app.business_logic.metrics.performance_metrics import (
    ResponseTimeCalculator,
    ResponseTimePercentileCalculator,
    ResponseTimeTrendCalculator
)
from app.business_logic.metrics.db_adapter import AsyncToSyncAdapter
from app.api.v1.metrics.utils import TimeRangeParams, format_response

router = APIRouter(prefix="/response_time", tags=["Performance Metrics"])

@router.get("/average", response_model=Dict[str, Any])
async def get_average_response_time(
    time_params: TimeRangeParams = Depends(),
    session: AsyncSession = Depends(get_session),
):
    """
    Get average response time metrics.
    
    Returns average response time along with min/max values and response count.
    """
    calculator = AsyncToSyncAdapter(ResponseTimeCalculator())
    result = await calculator.calculate(
        db=session,
        start_time=time_params.start_time,
        end_time=time_params.end_time,
        agent_id=time_params.agent_id,
        session_id=time_params.session_id
    )
    
    return format_response(result, time_params.get_metadata())

@router.get("/percentiles", response_model=Dict[str, Any])
async def get_response_time_percentiles(
    time_params: TimeRangeParams = Depends(),
    percentiles: List[int] = Query([50, 90, 95, 99], description="Percentiles to calculate"),
    session: AsyncSession = Depends(get_session),
):
    """
    Get response time percentiles.
    
    Returns response time values at specified percentiles.
    """
    calculator = AsyncToSyncAdapter(ResponseTimePercentileCalculator())
    result = await calculator.calculate(
        db=session,
        start_time=time_params.start_time,
        end_time=time_params.end_time,
        agent_id=time_params.agent_id,
        session_id=time_params.session_id,
        percentiles=percentiles
    )
    
    metadata = time_params.get_metadata()
    metadata["percentiles"] = percentiles
    
    return format_response(result, metadata)

@router.get("/trend", response_model=Dict[str, Any])
async def get_response_time_trend(
    time_params: TimeRangeParams = Depends(),
    interval: str = Query("hour", description="Time interval for trend data (minute, hour, day)"),
    session: AsyncSession = Depends(get_session),
):
    """
    Get response time trend over time.
    
    Returns time series data for response time metrics.
    """
    calculator = AsyncToSyncAdapter(ResponseTimeTrendCalculator())
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