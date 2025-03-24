from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from app.database.init_db import get_session
from app.business_logic.metrics.token_usage_metrics import (
    TotalTokenUsageCalculator,
    AverageTokenUsageCalculator,
    ModelTokenUsageCalculator
)
from app.business_logic.metrics.db_adapter import AsyncToSyncAdapter
from app.api.v1.metrics.utils import TimeRangeParams, format_response

router = APIRouter(prefix="/token_usage", tags=["Token Usage Metrics"])

@router.get("/total", response_model=Dict[str, Any])
async def get_total_token_usage(
    time_params: TimeRangeParams = Depends(),
    session: AsyncSession = Depends(get_session),
):
    """
    Get total token usage metrics.
    
    Returns total input, output, and combined token usage for the specified time period.
    """
    calculator = AsyncToSyncAdapter(TotalTokenUsageCalculator())
    result = await calculator.calculate(
        db=session,
        start_time=time_params.start_time,
        end_time=time_params.end_time,
        agent_id=time_params.agent_id,
        session_id=time_params.session_id
    )
    
    return format_response(result, time_params.get_metadata())

@router.get("/average", response_model=Dict[str, Any])
async def get_average_token_usage(
    time_params: TimeRangeParams = Depends(),
    session: AsyncSession = Depends(get_session),
):
    """
    Get average token usage metrics per request.
    
    Returns average input, output, and combined token usage per request.
    """
    calculator = AsyncToSyncAdapter(AverageTokenUsageCalculator())
    result = await calculator.calculate(
        db=session,
        start_time=time_params.start_time,
        end_time=time_params.end_time,
        agent_id=time_params.agent_id,
        session_id=time_params.session_id
    )
    
    return format_response(result, time_params.get_metadata())

@router.get("/by_model", response_model=Dict[str, Any])
async def get_token_usage_by_model(
    time_params: TimeRangeParams = Depends(),
    model_name: Optional[str] = Query(None, description="Filter by model name"),
    top_n: int = Query(10, description="Number of top models to include"),
    session: AsyncSession = Depends(get_session),
):
    """
    Get token usage breakdown by model.
    
    Returns token usage statistics for each model, or for a specific model if provided.
    """
    calculator = AsyncToSyncAdapter(ModelTokenUsageCalculator())
    result = await calculator.calculate(
        db=session,
        start_time=time_params.start_time,
        end_time=time_params.end_time,
        agent_id=time_params.agent_id,
        session_id=time_params.session_id,
        model_name=model_name,
        top_n=top_n
    )
    
    metadata = time_params.get_metadata()
    metadata["model_name"] = model_name
    metadata["top_n"] = top_n
    
    return format_response(result, metadata) 