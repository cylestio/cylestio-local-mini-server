from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.future import select
from typing import List, Optional
import datetime

from app.database.init_db import get_session
from app.models.agent import Agent
from app.models.event import Event

router = APIRouter()

@router.get("/", response_model=List[dict])
async def get_all_agents(
    session: AsyncSession = Depends(get_session),
    skip: int = 0,
    limit: int = 100
):
    """Get all registered agents."""
    
    # Execute query to get agents with last seen time and event count
    result = await session.execute(
        select(
            Agent.agent_id,
            Agent.first_seen,
            Agent.last_seen,
            Agent.llm_provider,
            func.count(Event.id).label("event_count")
        )
        .outerjoin(Event, Agent.agent_id == Event.agent_id)
        .group_by(Agent.agent_id)
        .order_by(Agent.last_seen.desc())
        .offset(skip)
        .limit(limit)
    )
    
    # Convert result to dictionaries
    agents = []
    for row in result:
        agents.append({
            "agent_id": row.agent_id,
            "first_seen": row.first_seen,
            "last_seen": row.last_seen,
            "llm_provider": row.llm_provider,
            "event_count": row.event_count
        })
    
    return agents

@router.get("/{agent_id}", response_model=dict)
async def get_agent(
    agent_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Get information about a specific agent."""
    
    # Get agent details
    result = await session.execute(
        select(Agent).where(Agent.agent_id == agent_id)
    )
    agent = result.scalars().first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID '{agent_id}' not found"
        )
    
    # Get event count for this agent
    event_count_result = await session.execute(
        select(func.count(Event.id)).where(Event.agent_id == agent_id)
    )
    event_count = event_count_result.scalar()
    
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
    
    return {
        "agent_id": agent.agent_id,
        "first_seen": agent.first_seen,
        "last_seen": agent.last_seen,
        "llm_provider": agent.llm_provider,
        "event_count": event_count,
        "latest_event": latest_event.event_type if latest_event else None,
        "latest_event_time": latest_event.timestamp if latest_event else None,
        "first_event": first_event.event_type if first_event else None,
        "first_event_time": first_event.timestamp if first_event else None,
    }

@router.get("/{agent_id}/summary", response_model=dict)
async def get_agent_summary(
    agent_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Get summary statistics for a specific agent."""
    
    # Verify agent exists
    result = await session.execute(
        select(Agent).where(Agent.agent_id == agent_id)
    )
    agent = result.scalars().first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID '{agent_id}' not found"
        )
    
    # Get event count by type
    event_types_result = await session.execute(
        select(Event.event_type, func.count(Event.id))
        .where(Event.agent_id == agent_id)
        .group_by(Event.event_type)
    )
    event_types = {event_type: count for event_type, count in event_types_result}
    
    # Get event count by channel
    channels_result = await session.execute(
        select(Event.channel, func.count(Event.id))
        .where(Event.agent_id == agent_id)
        .group_by(Event.channel)
    )
    channels = {channel: count for channel, count in channels_result}
    
    # Calculate average response time (duration_ms) for model responses
    avg_response_time_result = await session.execute(
        select(func.avg(Event.duration_ms))
        .where(Event.agent_id == agent_id)
        .where(Event.event_type.in_(["model_response", "LLM_call_finish"]))
    )
    avg_response_time = avg_response_time_result.scalar() or 0
    
    return {
        "agent_id": agent.agent_id,
        "event_count_by_type": event_types,
        "event_count_by_channel": channels,
        "avg_response_time_ms": avg_response_time,
        "first_seen": agent.first_seen,
        "last_seen": agent.last_seen,
    } 