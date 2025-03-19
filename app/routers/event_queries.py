from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, asc, and_
from typing import List, Optional
import datetime

from app.database.init_db import get_session
from app.models.event import Event

router = APIRouter()

@router.get("/", response_model=List[dict])
async def get_events(
    agent_id: Optional[str] = None,
    event_type: Optional[str] = None,
    channel: Optional[str] = None,
    level: Optional[str] = None,
    session_id: Optional[str] = None,
    from_time: Optional[str] = None,
    to_time: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    sort: str = "desc",
    session: AsyncSession = Depends(get_session)
):
    """Get events with filtering options."""
    
    # Build query with filters
    query = select(Event)
    
    if agent_id:
        query = query.where(Event.agent_id == agent_id)
    
    if event_type:
        query = query.where(Event.event_type == event_type)
    
    if channel:
        query = query.where(Event.channel == channel)
    
    if level:
        query = query.where(Event.level == level)
    
    if session_id:
        query = query.where(Event.session_id == session_id)
    
    if from_time:
        from_datetime = datetime.datetime.fromisoformat(from_time.replace("Z", "+00:00"))
        query = query.where(Event.timestamp >= from_datetime)
    
    if to_time:
        to_datetime = datetime.datetime.fromisoformat(to_time.replace("Z", "+00:00"))
        query = query.where(Event.timestamp <= to_datetime)
    
    # Apply sorting
    if sort.lower() == "asc":
        query = query.order_by(asc(Event.timestamp))
    else:
        query = query.order_by(desc(Event.timestamp))
    
    # Apply pagination
    query = query.offset(offset).limit(limit)
    
    # Execute query
    result = await session.execute(query)
    events = result.scalars().all()
    
    # Convert to dictionaries
    event_list = []
    for event in events:
        event_dict = {
            "id": event.id,
            "timestamp": event.timestamp,
            "level": event.level,
            "agent_id": event.agent_id,
            "event_type": event.event_type,
            "channel": event.channel,
            "direction": event.direction,
            "session_id": event.session_id,
            "duration_ms": event.duration_ms,
            "data": event.data
        }
        event_list.append(event_dict)
    
    return event_list

@router.get("/{event_id}", response_model=dict)
async def get_event(
    event_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Get a specific event by ID."""
    
    result = await session.execute(
        select(Event).where(Event.id == event_id)
    )
    event = result.scalars().first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID {event_id} not found"
        )
    
    return {
        "id": event.id,
        "timestamp": event.timestamp,
        "level": event.level,
        "agent_id": event.agent_id,
        "event_type": event.event_type,
        "channel": event.channel,
        "direction": event.direction,
        "session_id": event.session_id,
        "duration_ms": event.duration_ms,
        "caller_file": event.caller_file,
        "caller_line": event.caller_line,
        "caller_function": event.caller_function,
        "data": event.data
    } 