from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from typing import List, Optional
import datetime

from app.database.init_db import get_session
from app.models.event import Event

router = APIRouter()

@router.get("/count", response_model=int)
async def get_event_count(
    agent_id: Optional[str] = None,
    session: AsyncSession = Depends(get_session)
):
    """Get the total number of events, optionally filtered by agent_id."""
    query = select(func.count(Event.id))
    
    if agent_id:
        query = query.where(Event.agent_id == agent_id)
        
    result = await session.execute(query)
    return result.scalar() or 0

@router.get("/by_level", response_model=dict)
async def get_events_by_level(
    agent_id: Optional[str] = None,
    from_time: Optional[str] = None,
    to_time: Optional[str] = None,
    session: AsyncSession = Depends(get_session)
):
    """Get event counts grouped by level."""
    query = select(Event.level, func.count(Event.id))
    
    # Apply filters
    filters = []
    if agent_id:
        filters.append(Event.agent_id == agent_id)
    
    if from_time:
        from_datetime = datetime.datetime.fromisoformat(from_time.replace("Z", "+00:00"))
        filters.append(Event.timestamp >= from_datetime)
    
    if to_time:
        to_datetime = datetime.datetime.fromisoformat(to_time.replace("Z", "+00:00"))
        filters.append(Event.timestamp <= to_datetime)
    
    if filters:
        query = query.where(and_(*filters))
    
    query = query.group_by(Event.level)
    
    result = await session.execute(query)
    return {level: count for level, count in result}

@router.get("/by_channel", response_model=dict)
async def get_events_by_channel(
    agent_id: Optional[str] = None,
    from_time: Optional[str] = None,
    to_time: Optional[str] = None,
    session: AsyncSession = Depends(get_session)
):
    """Get event counts grouped by channel."""
    query = select(Event.channel, func.count(Event.id))
    
    # Apply filters
    filters = []
    if agent_id:
        filters.append(Event.agent_id == agent_id)
    
    if from_time:
        from_datetime = datetime.datetime.fromisoformat(from_time.replace("Z", "+00:00"))
        filters.append(Event.timestamp >= from_datetime)
    
    if to_time:
        to_datetime = datetime.datetime.fromisoformat(to_time.replace("Z", "+00:00"))
        filters.append(Event.timestamp <= to_datetime)
    
    if filters:
        query = query.where(and_(*filters))
    
    query = query.group_by(Event.channel)
    
    result = await session.execute(query)
    return {channel: count for channel, count in result}

@router.get("/by_type", response_model=dict)
async def get_events_by_type(
    agent_id: Optional[str] = None,
    from_time: Optional[str] = None,
    to_time: Optional[str] = None,
    session: AsyncSession = Depends(get_session)
):
    """Get event counts grouped by event_type."""
    query = select(Event.event_type, func.count(Event.id))
    
    # Apply filters
    filters = []
    if agent_id:
        filters.append(Event.agent_id == agent_id)
    
    if from_time:
        from_datetime = datetime.datetime.fromisoformat(from_time.replace("Z", "+00:00"))
        filters.append(Event.timestamp >= from_datetime)
    
    if to_time:
        to_datetime = datetime.datetime.fromisoformat(to_time.replace("Z", "+00:00"))
        filters.append(Event.timestamp <= to_datetime)
    
    if filters:
        query = query.where(and_(*filters))
    
    query = query.group_by(Event.event_type)
    
    result = await session.execute(query)
    return {event_type: count for event_type, count in result}

@router.get("/timeseries", response_model=List[dict])
async def get_events_timeseries(
    agent_id: Optional[str] = None,
    event_type: Optional[str] = None,
    channel: Optional[str] = None,
    from_time: Optional[str] = None,
    to_time: Optional[str] = None,
    interval: str = "hour",
    session: AsyncSession = Depends(get_session)
):
    """Get time series data for events."""
    
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
    
    # Determine the interval function based on the requested interval
    if interval == "minute":
        interval_fn = func.strftime("%Y-%m-%d %H:%M:00", Event.timestamp)
    elif interval == "hour":
        interval_fn = func.strftime("%Y-%m-%d %H:00:00", Event.timestamp)
    elif interval == "day":
        interval_fn = func.strftime("%Y-%m-%d", Event.timestamp)
    elif interval == "month":
        interval_fn = func.strftime("%Y-%m", Event.timestamp)
    else:
        # Default to hour
        interval_fn = func.strftime("%Y-%m-%d %H:00:00", Event.timestamp)
    
    # Build query with filters
    query = select(
        interval_fn.label("interval"),
        func.count(Event.id).label("count")
    )
    
    filters = []
    if agent_id:
        filters.append(Event.agent_id == agent_id)
    
    if event_type:
        filters.append(Event.event_type == event_type)
    
    if channel:
        filters.append(Event.channel == channel)
    
    filters.extend([
        Event.timestamp >= from_datetime,
        Event.timestamp <= to_datetime
    ])
    
    query = query.where(and_(*filters))
    query = query.group_by("interval").order_by("interval")
    
    # Execute query
    result = await session.execute(query)
    
    return [
        {
            "interval": interval,
            "count": count
        }
        for interval, count in result
    ] 