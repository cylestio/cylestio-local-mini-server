from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List

from app.database.init_db import get_session
from app.models.agent import Agent

router = APIRouter()

@router.get("/count", response_model=int)
async def get_agent_count(
    session: AsyncSession = Depends(get_session)
):
    """Get the total number of agents."""
    result = await session.execute(select(func.count(Agent.id)))
    return result.scalar() or 0

@router.get("/recent", response_model=List[dict])
async def get_recent_agents(
    limit: int = 5,
    session: AsyncSession = Depends(get_session)
):
    """Get the most recently active agents."""
    result = await session.execute(
        select(Agent)
        .order_by(Agent.last_seen.desc())
        .limit(limit)
    )
    
    return [
        {
            "agent_id": agent.agent_id,
            "last_seen": agent.last_seen,
            "first_seen": agent.first_seen,
            "llm_provider": agent.llm_provider
        }
        for agent in result.scalars().all()
    ]

@router.get("/providers", response_model=dict)
async def get_llm_providers(
    session: AsyncSession = Depends(get_session)
):
    """Get counts of agents by LLM provider."""
    result = await session.execute(
        select(Agent.llm_provider, func.count(Agent.id))
        .group_by(Agent.llm_provider)
    )
    
    return {
        provider if provider else "unknown": count 
        for provider, count in result
    } 