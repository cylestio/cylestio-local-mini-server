from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any
import datetime

from app.database.init_db import get_session
from app.models.agent import Agent
from app.models.event import Event
from app.models.session import Session

router = APIRouter()

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_event(
    event_data: Dict[str, Any] = Body(...),
    session: AsyncSession = Depends(get_session)
):
    """Create a new event from telemetry data."""
    
    # Extract required fields
    try:
        timestamp = event_data.get("timestamp")
        level = event_data.get("level", "INFO")
        agent_id = event_data.get("agent_id")
        event_type = event_data.get("event_type")
        channel = event_data.get("channel", "UNKNOWN")
        
        # Convert timestamp to datetime if it's a string
        if isinstance(timestamp, str):
            timestamp = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        
        # Optional fields
        direction = event_data.get("direction")
        session_id = event_data.get("session_id")
        
        # Check if we have performance data
        duration_ms = None
        if "data" in event_data and "performance" in event_data["data"]:
            if "duration_ms" in event_data["data"]:
                duration_ms = event_data["data"]["duration_ms"]
            elif isinstance(event_data["data"]["performance"], dict) and "duration_ms" in event_data["data"]["performance"]:
                duration_ms = event_data["data"]["performance"]["duration_ms"]
        
        # Check for caller information
        caller_file = None
        caller_line = None
        caller_function = None
        if "caller" in event_data:
            caller = event_data["caller"]
            caller_file = caller.get("file")
            caller_line = caller.get("line")
            caller_function = caller.get("function")
        
    except (KeyError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid event data: {str(e)}"
        )
    
    # Check if agent exists, create if not
    agent_result = await session.execute(
        select(Agent).where(Agent.agent_id == agent_id)
    )
    agent = agent_result.scalars().first()
    
    if not agent:
        # Create new agent
        agent = Agent(
            agent_id=agent_id,
            first_seen=timestamp,
            last_seen=timestamp
        )
        
        # Set LLM provider if available
        if "data" in event_data and "model" in event_data["data"]:
            agent.llm_provider = event_data["data"]["model"]
        elif "data" in event_data and "LLM_provider" in event_data["data"]:
            agent.llm_provider = event_data["data"]["LLM_provider"]
        
        session.add(agent)
    else:
        # Update last seen
        agent.last_seen = timestamp
    
    # Create event
    event = Event(
        timestamp=timestamp,
        level=level,
        agent_id=agent_id,
        event_type=event_type,
        channel=channel,
        direction=direction,
        session_id=session_id,
        data=event_data.get("data"),
        duration_ms=duration_ms,
        caller_file=caller_file,
        caller_line=caller_line,
        caller_function=caller_function
    )
    session.add(event)
    
    # Check for session and update if needed
    if session_id:
        session_result = await session.execute(
            select(Session).where(Session.session_id == session_id)
        )
        existing_session = session_result.scalars().first()
        
        if not existing_session:
            # Create new session
            new_session = Session(
                session_id=session_id,
                agent_id=agent_id,
                start_time=timestamp,
                total_events=1
            )
            session.add(new_session)
        else:
            # Update session
            existing_session.end_time = timestamp
            existing_session.total_events += 1
    
    await session.commit()
    
    return {"status": "success", "message": "Event recorded successfully"} 