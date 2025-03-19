from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_
from typing import List, Optional
from datetime import datetime

from app.database.init_db import get_session
from app.models.agent import Agent
from app.models.event import Event

router = APIRouter()

@router.get("/", response_model=dict)
async def list_agents(
    start_time: Optional[str] = Query(None, description="Start time in ISO format"),
    end_time: Optional[str] = Query(None, description="End time in ISO format"),
    limit: int = Query(20, ge=1, le=100, description="Number of agents to return"),
    offset: int = Query(0, ge=0, description="Number of agents to skip"),
    sort_by: str = Query("last_seen", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)"),
    session: AsyncSession = Depends(get_session)
):
    """
    List all agents with their status.
    
    Returns a paginated list of agents with their basic information and status.
    """
    # Build the base query
    query = select(
        Agent.agent_id,
        Agent.first_seen,
        Agent.last_seen,
        Agent.llm_provider,
        func.count(Event.id).label("event_count")
    ).outerjoin(Event, Agent.agent_id == Event.agent_id)
    
    # Apply time filters if provided
    filters = []
    if start_time:
        start_datetime = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        filters.append(Agent.last_seen >= start_datetime)
    
    if end_time:
        end_datetime = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        filters.append(Agent.last_seen <= end_datetime)
    
    if filters:
        query = query.where(and_(*filters))
    
    # Group by agent
    query = query.group_by(Agent.agent_id)
    
    # Apply sorting
    if sort_by == "agent_id":
        sort_col = Agent.agent_id
    elif sort_by == "first_seen":
        sort_col = Agent.first_seen
    elif sort_by == "last_seen":
        sort_col = Agent.last_seen
    elif sort_by == "event_count":
        sort_col = func.count(Event.id)
    else:
        sort_col = Agent.last_seen  # Default
    
    if sort_order.lower() == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())
    
    # Get total count for pagination
    count_query = select(func.count(Agent.agent_id.distinct()))
    if filters:
        count_query = count_query.where(and_(*filters))
    
    count_result = await session.execute(count_query)
    total_count = count_result.scalar()
    
    # Apply pagination
    query = query.offset(offset).limit(limit)
    
    # Execute the query
    result = await session.execute(query)
    
    # Convert result to list of dictionaries
    agents = []
    for row in result:
        status = "active" if (datetime.utcnow() - row.last_seen).total_seconds() < 3600 else "inactive"
        agents.append({
            "agent_id": row.agent_id,
            "first_seen": row.first_seen.isoformat(),
            "last_seen": row.last_seen.isoformat(),
            "llm_provider": row.llm_provider,
            "event_count": row.event_count,
            "status": status
        })
    
    # Construct response with pagination metadata
    return {
        "results": agents,
        "pagination": {
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count
        }
    }

@router.get("/{agent_id}", response_model=dict)
async def get_agent_details(
    agent_id: str,
    session: AsyncSession = Depends(get_session)
):
    """
    Get detailed information about a specific agent.
    """
    # Get agent details
    agent_result = await session.execute(
        select(Agent).where(Agent.agent_id == agent_id)
    )
    agent = agent_result.scalars().first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID '{agent_id}' not found"
        )
    
    # Get event counts by type
    event_types_result = await session.execute(
        select(Event.event_type, func.count(Event.id))
        .where(Event.agent_id == agent_id)
        .group_by(Event.event_type)
    )
    event_types = {event_type: count for event_type, count in event_types_result}
    
    # Get event counts by channel
    channels_result = await session.execute(
        select(Event.channel, func.count(Event.id))
        .where(Event.agent_id == agent_id)
        .group_by(Event.channel)
    )
    channels = {channel: count for channel, count in channels_result}
    
    # Get latest event
    latest_event_result = await session.execute(
        select(Event)
        .where(Event.agent_id == agent_id)
        .order_by(Event.timestamp.desc())
        .limit(1)
    )
    latest_event = latest_event_result.scalars().first()
    
    # Get first event
    first_event_result = await session.execute(
        select(Event)
        .where(Event.agent_id == agent_id)
        .order_by(Event.timestamp.asc())
        .limit(1)
    )
    first_event = first_event_result.scalars().first()
    
    # Calculate status
    status = "active" if (datetime.utcnow() - agent.last_seen).total_seconds() < 3600 else "inactive"
    
    # Calculate average response time for model responses
    avg_response_time_result = await session.execute(
        select(func.avg(Event.duration_ms))
        .where(Event.agent_id == agent_id)
        .where(Event.event_type.in_(["model_response", "LLM_call_finish"]))
    )
    avg_response_time = avg_response_time_result.scalar() or 0
    
    # Construct the response
    return {
        "agent_id": agent.agent_id,
        "first_seen": agent.first_seen.isoformat(),
        "last_seen": agent.last_seen.isoformat(),
        "llm_provider": agent.llm_provider,
        "status": status,
        "event_counts": {
            "by_type": event_types,
            "by_channel": channels,
            "total": sum(event_types.values())
        },
        "performance": {
            "avg_response_time_ms": round(avg_response_time, 2)
        },
        "latest_event": {
            "type": latest_event.event_type if latest_event else None,
            "timestamp": latest_event.timestamp.isoformat() if latest_event else None
        },
        "first_event": {
            "type": first_event.event_type if first_event else None,
            "timestamp": first_event.timestamp.isoformat() if first_event else None
        }
    } 