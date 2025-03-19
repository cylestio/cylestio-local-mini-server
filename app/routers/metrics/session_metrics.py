from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List, Optional
import datetime

from app.database.init_db import get_session
from app.models.session import Session

router = APIRouter()

@router.get("/count", response_model=int)
async def get_session_count(
    agent_id: Optional[str] = None,
    session: AsyncSession = Depends(get_session)
):
    """Get the total number of sessions."""
    query = select(func.count(Session.id))
    
    if agent_id:
        query = query.where(Session.agent_id == agent_id)
        
    result = await session.execute(query)
    return result.scalar() or 0

@router.get("/recent", response_model=List[dict])
async def get_recent_sessions(
    agent_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    session: AsyncSession = Depends(get_session)
):
    """Get recent sessions with event counts and duration."""
    
    # Build query
    query = select(
        Session.session_id,
        Session.agent_id,
        Session.start_time,
        Session.end_time,
        Session.total_events
    )
    
    if agent_id:
        query = query.where(Session.agent_id == agent_id)
    
    query = query.order_by(Session.start_time.desc()).offset(offset).limit(limit)
    
    # Execute query
    result = await session.execute(query)
    
    # Convert to list of dictionaries
    sessions = []
    for row in result:
        sessions.append({
            "session_id": row.session_id,
            "agent_id": row.agent_id,
            "start_time": row.start_time,
            "end_time": row.end_time,
            "duration": (row.end_time - row.start_time).total_seconds() if row.end_time else None,
            "total_events": row.total_events
        })
    
    return sessions

@router.get("/avg_duration", response_model=float)
async def get_avg_session_duration(
    agent_id: Optional[str] = None,
    from_time: Optional[str] = None,
    to_time: Optional[str] = None,
    session: AsyncSession = Depends(get_session)
):
    """Get the average session duration in seconds."""
    
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
    
    # Build query
    query = select(
        func.avg(func.strftime("%s", Session.end_time) - func.strftime("%s", Session.start_time))
    ).where(
        Session.end_time != None
    )
    
    if agent_id:
        query = query.where(Session.agent_id == agent_id)
    
    query = query.where(Session.start_time >= from_datetime, Session.start_time <= to_datetime)
    
    # Execute query
    result = await session.execute(query)
    avg_duration = result.scalar()
    
    return avg_duration or 0.0

@router.get("/avg_events_per_session", response_model=float)
async def get_avg_events_per_session(
    agent_id: Optional[str] = None,
    from_time: Optional[str] = None,
    to_time: Optional[str] = None,
    session: AsyncSession = Depends(get_session)
):
    """Get the average number of events per session."""
    
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
    
    # Build query
    query = select(func.avg(Session.total_events))
    
    if agent_id:
        query = query.where(Session.agent_id == agent_id)
    
    query = query.where(Session.start_time >= from_datetime, Session.start_time <= to_datetime)
    
    # Execute query
    result = await session.execute(query)
    avg_events = result.scalar()
    
    return avg_events or 0.0 