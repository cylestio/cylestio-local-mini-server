from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List, Optional, Dict
import datetime
import statistics

from app.database.init_db import get_session
from app.models.event import Event

router = APIRouter()

@router.get("/response_times", response_model=Dict)
async def get_response_times(
    agent_id: Optional[str] = None,
    from_time: Optional[str] = None,
    to_time: Optional[str] = None,
    session: AsyncSession = Depends(get_session)
):
    """Get performance statistics for model responses."""
    
    # Convert time strings to datetime objects
    now = datetime.datetime.now(datetime.UTC)
    if from_time:
        from_datetime = datetime.datetime.fromisoformat(from_time.replace("Z", "+00:00"))
    else:
        # Default to 7 days ago
        from_datetime = now - datetime.timedelta(days=7)
    
    if to_time:
        to_datetime = datetime.datetime.fromisoformat(to_time.replace("Z", "+00:00"))
    else:
        to_datetime = now
    
    # Build query for model response events
    query = select(Event.duration_ms).where(
        and_(
            Event.event_type.in_(["model_response", "LLM_call_finish"]),
            Event.timestamp >= from_datetime,
            Event.timestamp <= to_datetime,
            Event.duration_ms != None
        )
    )
    
    if agent_id:
        query = query.where(Event.agent_id == agent_id)
    
    # Execute query
    result = await session.execute(query)
    durations = [row.duration_ms for row in result if row.duration_ms is not None]
    
    # Calculate statistics
    if durations:
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        min_duration = min(durations)
        median_duration = statistics.median(durations)
        
        # Calculate percentiles
        sorted_durations = sorted(durations)
        p90_idx = int(len(sorted_durations) * 0.90)
        p95_idx = int(len(sorted_durations) * 0.95)
        p99_idx = int(len(sorted_durations) * 0.99)
        
        return {
            "avg_duration_ms": avg_duration,
            "median_duration_ms": median_duration,
            "max_duration_ms": max_duration,
            "min_duration_ms": min_duration,
            "p90_duration_ms": sorted_durations[p90_idx],
            "p95_duration_ms": sorted_durations[p95_idx],
            "p99_duration_ms": sorted_durations[p99_idx],
            "total_requests": len(durations)
        }
    else:
        return {
            "avg_duration_ms": 0,
            "median_duration_ms": 0,
            "max_duration_ms": 0,
            "min_duration_ms": 0,
            "p90_duration_ms": 0,
            "p95_duration_ms": 0,
            "p99_duration_ms": 0,
            "total_requests": 0
        }

@router.get("/requests_by_day", response_model=List[Dict])
async def get_requests_by_day(
    agent_id: Optional[str] = None,
    from_time: Optional[str] = None,
    to_time: Optional[str] = None,
    session: AsyncSession = Depends(get_session)
):
    """Get count of LLM requests by day."""
    
    # Convert time strings to datetime objects
    now = datetime.datetime.now(datetime.UTC)
    if from_time:
        from_datetime = datetime.datetime.fromisoformat(from_time.replace("Z", "+00:00"))
    else:
        # Default to 30 days ago
        from_datetime = now - datetime.timedelta(days=30)
    
    if to_time:
        to_datetime = datetime.datetime.fromisoformat(to_time.replace("Z", "+00:00"))
    else:
        to_datetime = now
    
    # Get count of requests by time range
    query = select(
        func.strftime("%Y-%m-%d", Event.timestamp).label("day"),
        func.count(Event.id).label("count")
    ).where(
        and_(
            Event.event_type.in_(["model_request", "LLM_call_start"]),
            Event.timestamp >= from_datetime,
            Event.timestamp <= to_datetime
        )
    )
    
    if agent_id:
        query = query.where(Event.agent_id == agent_id)
    
    query = query.group_by("day").order_by("day")
    
    result = await session.execute(query)
    
    return [
        {
            "day": day,
            "count": count
        }
        for day, count in result
    ] 