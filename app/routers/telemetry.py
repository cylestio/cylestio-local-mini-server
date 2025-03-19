from fastapi import APIRouter, Depends, HTTPException, status, Body, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any, List, Optional
import datetime
import asyncio
import logging

from app.database.init_db import get_session
from app.models.agent import Agent
from app.models.event import Event
from app.models.session import Session

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

async def process_event(event_data: Dict[str, Any], session: AsyncSession):
    """
    Process a telemetry event asynchronously.
    This function handles database operations for storing the event.
    """
    try:
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
            # Log the error but don't raise an exception here as this is in a background task
            logger.error(f"Error processing event: {str(e)}")
            return
        
        # Check if agent exists, create if not
        try:
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
        except Exception as e:
            logger.error(f"Error checking agent: {str(e)}")
            # Continue anyway, we'll still try to store the event
        
        # Create event
        try:
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
        except Exception as e:
            logger.error(f"Error creating event: {str(e)}")
            return
        
        # Check for session and update if needed
        if session_id:
            try:
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
            except Exception as e:
                logger.error(f"Error updating session: {str(e)}")
                # Continue anyway
        
        await session.commit()
    except Exception as e:
        logger.error(f"Unhandled error in process_event: {str(e)}")
        # We catch all exceptions to prevent background task failures

def validate_telemetry_event(event_data: Dict[str, Any]) -> List[str]:
    """
    Validate the telemetry event data and return a list of validation errors.
    If the list is empty, the event is valid.
    """
    errors = []
    
    # Check for required fields
    if "timestamp" not in event_data:
        errors.append("Missing required field: timestamp")
    
    if "agent_id" not in event_data:
        errors.append("Missing required field: agent_id")
    
    if "event_type" not in event_data:
        errors.append("Missing required field: event_type")
    
    return errors

@router.post("/v1/telemetry", status_code=status.HTTP_202_ACCEPTED)
async def ingest_telemetry(
    background_tasks: BackgroundTasks,
    event_data: Dict[str, Any] = Body(...),
    db_session: AsyncSession = Depends(get_session)
):
    """
    Ingest a telemetry event from the monitoring SDK.
    This endpoint quickly validates the event and queues it for processing.
    """
    # Validate the event data
    validation_errors = validate_telemetry_event(event_data)
    if validation_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": validation_errors}
        )
    
    # Queue the event for asynchronous processing
    background_tasks.add_task(process_event, event_data, db_session)
    
    # Return a quick acknowledgement
    return {"status": "accepted", "message": "Event queued for processing"} 