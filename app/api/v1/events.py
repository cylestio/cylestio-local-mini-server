from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc, and_, or_
from typing import List, Optional
from datetime import datetime

from app.database.init_db import get_session
from app.models.event import Event

router = APIRouter()

@router.get("/{agent_id}/events", response_model=dict)
async def get_agent_events(
    agent_id: str,
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    level: Optional[str] = Query(None, description="Filter by event level"),
    channel: Optional[str] = Query(None, description="Filter by channel"),
    start_time: Optional[str] = Query(None, description="Start time in ISO format"),
    end_time: Optional[str] = Query(None, description="End time in ISO format"),
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    limit: int = Query(50, ge=1, le=200, description="Number of events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)"),
    session: AsyncSession = Depends(get_session)
):
    """
    Get events for a specific agent with filtering options.
    
    Returns a paginated list of events for the specified agent.
    """
    # Build the base query
    query = select(Event).where(Event.agent_id == agent_id)
    
    # Apply filters
    filters = []
    
    if event_type:
        # Support comma-separated list of event types
        event_types = [t.strip() for t in event_type.split(",")]
        if len(event_types) == 1:
            filters.append(Event.event_type == event_types[0])
        else:
            filters.append(Event.event_type.in_(event_types))
    
    if level:
        # Support comma-separated list of levels
        levels = [l.strip() for l in level.split(",")]
        if len(levels) == 1:
            filters.append(Event.level == levels[0])
        else:
            filters.append(Event.level.in_(levels))
    
    if channel:
        # Support comma-separated list of channels
        channels = [c.strip() for c in channel.split(",")]
        if len(channels) == 1:
            filters.append(Event.channel == channels[0])
        else:
            filters.append(Event.channel.in_(channels))
    
    if session_id:
        filters.append(Event.session_id == session_id)
    
    if start_time:
        start_datetime = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        filters.append(Event.timestamp >= start_datetime)
    
    if end_time:
        end_datetime = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        filters.append(Event.timestamp <= end_datetime)
    
    if filters:
        query = query.where(and_(*filters))
    
    # Get total count for pagination
    count_query = select(func.count()).select_from(Event).where(Event.agent_id == agent_id)
    if filters:
        count_query = count_query.where(and_(*filters))
    
    count_result = await session.execute(count_query)
    total_count = count_result.scalar()
    
    # Apply sorting
    if sort_order.lower() == "asc":
        query = query.order_by(asc(Event.timestamp))
    else:
        query = query.order_by(desc(Event.timestamp))
    
    # Apply pagination
    query = query.offset(offset).limit(limit)
    
    # Execute the query
    result = await session.execute(query)
    events = result.scalars().all()
    
    # Convert to list of dictionaries
    event_list = []
    for event in events:
        event_list.append({
            "id": event.id,
            "timestamp": event.timestamp.isoformat(),
            "level": event.level,
            "event_type": event.event_type,
            "channel": event.channel,
            "direction": event.direction,
            "session_id": event.session_id,
            "duration_ms": event.duration_ms,
            "relationship_id": event.relationship_id,
            "data": event.data
        })
    
    # Construct response with pagination metadata
    return {
        "results": event_list,
        "pagination": {
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count
        }
    }

@router.get("/{agent_id}/events/{event_id}", response_model=dict)
async def get_agent_event(
    agent_id: str,
    event_id: int,
    session: AsyncSession = Depends(get_session)
):
    """
    Get detailed information about a specific event for an agent.
    """
    result = await session.execute(
        select(Event)
        .where(Event.id == event_id)
        .where(Event.agent_id == agent_id)
    )
    event = result.scalars().first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID {event_id} not found for agent {agent_id}"
        )
    
    # Get all related events (same relationship_id) if a relationship_id exists
    related_events = []
    if event.relationship_id:
        related_query = await session.execute(
            select(Event)
            .where(Event.relationship_id == event.relationship_id)
            .where(Event.id != event.id)  # Exclude the current event
            .order_by(Event.timestamp)
        )
        related_events = related_query.scalars().all()
    
    # Construct the response
    return {
        "id": event.id,
        "timestamp": event.timestamp.isoformat(),
        "level": event.level,
        "agent_id": event.agent_id,
        "event_type": event.event_type,
        "channel": event.channel,
        "direction": event.direction,
        "session_id": event.session_id,
        "relationship_id": event.relationship_id,
        "duration_ms": event.duration_ms,
        "caller_file": event.caller_file,
        "caller_line": event.caller_line,
        "caller_function": event.caller_function,
        "data": event.data,
        "related_events": [
            {
                "id": e.id,
                "timestamp": e.timestamp.isoformat(),
                "event_type": e.event_type,
                "level": e.level
            } 
            for e in related_events
        ]
    } 