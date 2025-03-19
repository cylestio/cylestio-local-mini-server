from fastapi import APIRouter, Depends, HTTPException, status, Body, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Dict, Any, List, Optional
import datetime
import asyncio
import logging
import json
import uuid

from app.database.init_db import get_session
from app.models.agent import Agent
from app.models.event import Event
from app.models.session import Session
from app.transformers.event_transformer import EventTransformer
from app.business_logic.event_processor import EventProcessor

# Configure logging
logger = logging.getLogger(__name__)

# Create router with a specific tag that won't be duplicated by the API router
router = APIRouter()
event_transformer = EventTransformer()

async def process_event(event_data: Dict[str, Any], session: AsyncSession):
    """
    Process a telemetry event asynchronously.
    This function handles database operations for storing the event.
    """
    try:
        # Transform the raw event data into structured data
        transformed_data = event_transformer.transform(event_data)
        
        # Extract required fields
        try:
            timestamp = transformed_data.get("timestamp")
            level = transformed_data.get("level", "INFO")
            agent_id = transformed_data.get("agent_id")
            event_type = transformed_data.get("event_type")
            channel = transformed_data.get("channel", "UNKNOWN")
            
            # Optional fields
            direction = transformed_data.get("direction")
            session_id = transformed_data.get("session_id")
            duration_ms = transformed_data.get("duration_ms")
            
            # Check for caller information
            caller_file = transformed_data.get("caller_file")
            caller_line = transformed_data.get("caller_line")
            caller_function = transformed_data.get("caller_function")
            
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
                
                # Set LLM provider if available from transformed data
                if "data" in transformed_data and transformed_data["data"].get("model"):
                    agent.llm_provider = transformed_data["data"].get("model")
                
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
                data=transformed_data.get("data"),
                duration_ms=duration_ms,
                caller_file=caller_file,
                caller_line=caller_line,
                caller_function=caller_function
            )
            session.add(event)
            await session.flush()  # Flush to get the ID
            
            # Process through business logic layer
            try:
                # Create event processor
                event_processor = EventProcessor()
                
                # Process the event with the business logic layer
                await event_processor.process_event(event, session)
                
                logger.info(f"Event {event.id} processed through business logic layer")
            except Exception as e:
                logger.error(f"Error processing event {event.id} through business logic layer: {str(e)}")
                # Continue anyway, we'll still commit the event
            
            # Find related event if this is a finish event
            if event_type in ["LLM_call_finish", "call_finish"]:
                related_event = await find_matching_start_event(agent_id, event, session)
                
                if related_event:
                    # Create a relationship ID
                    relationship_id = str(uuid.uuid4())
                    
                    # Update the current (finish) event
                    event.direction = "incoming"
                    event.relationship_id = relationship_id
                    
                    # Update the related (start) event
                    await session.execute(
                        update(Event)
                        .where(Event.id == related_event.id)
                        .values(
                            direction="outgoing",
                            relationship_id=relationship_id
                        )
                    )
                    
                    # Calculate duration if not already present
                    if not duration_ms and related_event.timestamp:
                        try:
                            start_time = related_event.timestamp
                            finish_time = timestamp
                            if isinstance(start_time, datetime.datetime) and isinstance(finish_time, datetime.datetime):
                                duration_ms = (finish_time - start_time).total_seconds() * 1000
                                event.duration_ms = duration_ms
                        except Exception as e:
                            logger.error(f"Error calculating duration: {str(e)}")
            
            # If this is a start event, ensure direction is set
            elif event_type in ["LLM_call_start", "call_start"]:
                event.direction = "outgoing"
                
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

async def find_matching_start_event(agent_id: str, finish_event: Event, session: AsyncSession) -> Optional[Event]:
    """
    Find a matching start event for a finish event using database lookup.
    
    Args:
        agent_id: Agent ID to look up events for
        finish_event: The finish event object
        session: Database session
        
    Returns:
        Matching start event if found, None otherwise
    """
    try:
        # Determine the corresponding start event type
        if finish_event.event_type == "LLM_call_finish":
            start_event_type = "LLM_call_start"
        elif finish_event.event_type == "call_finish":
            start_event_type = "call_start"
        else:
            return None  # Not a finish event type we handle
        
        # Build the base query to find unmatched start events
        query = (
            select(Event)
            .where(
                Event.agent_id == agent_id,
                Event.event_type == start_event_type,
                Event.relationship_id == None,
                Event.timestamp <= finish_event.timestamp
            )
            .order_by(Event.timestamp.desc())
        )
        
        # Additional matching criteria based on event type
        if start_event_type == "LLM_call_start" and finish_event.data and "model" in finish_event.data:
            # For LLM calls, try to match events with the same model if available
            # This requires database-specific JSON operators
            # Note: The exact syntax may vary depending on the database (PostgreSQL, SQLite, etc.)
            # This example is for PostgreSQL, would need to be adapted for other databases
            model = finish_event.data.get("model")
            if model:
                logger.info(f"Looking for LLM start event with model: {model}")
                # We'll use the base query without additional filters for now
                # In a production environment with PostgreSQL, you could use JSON operators
        
        elif start_event_type == "call_start" and finish_event.data and "tool_name" in finish_event.data:
            # For tool calls, try to match events with the same tool name if available
            tool_name = finish_event.data.get("tool_name")
            if tool_name:
                logger.info(f"Looking for tool start event with name: {tool_name}")
                # Similar to above, we'll use the base query for now
        
        # Execute the query
        result = await session.execute(query)
        start_event = result.scalars().first()
        
        if start_event:
            logger.info(f"Found matching {start_event_type} event with ID: {start_event.id}")
            return start_event
        else:
            logger.info(f"No matching {start_event_type} event found for {finish_event.event_type}")
            return None
            
    except Exception as e:
        logger.error(f"Error finding matching start event: {str(e)}")
        return None

async def process_batch(event_data_list: List[Dict[str, Any]], session: AsyncSession):
    """
    Process a batch of telemetry events with relationship tracking.
    Utilizes the event transformer's batch processing capabilities.
    """
    try:
        # Transform the batch of events
        transformed_events = event_transformer.process_batch(event_data_list)
        
        # Process each transformed event
        for transformed_data in transformed_events:
            try:
                # Extract required fields
                timestamp = transformed_data.get("timestamp")
                level = transformed_data.get("level", "INFO")
                agent_id = transformed_data.get("agent_id")
                event_type = transformed_data.get("event_type")
                channel = transformed_data.get("channel", "UNKNOWN")
                
                # Optional fields
                direction = transformed_data.get("direction")
                session_id = transformed_data.get("session_id")
                duration_ms = transformed_data.get("duration_ms")
                relationship_id = transformed_data.get("relationship_id")
                related_event_id = transformed_data.get("related_event_id")
                
                # Check for caller information
                caller_file = transformed_data.get("caller_file")
                caller_line = transformed_data.get("caller_line")
                caller_function = transformed_data.get("caller_function")
                
                # Check if agent exists, create if not (only do this once per batch per agent)
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
                    
                    # Set LLM provider if available from transformed data
                    if "data" in transformed_data and transformed_data["data"].get("model"):
                        agent.llm_provider = transformed_data["data"].get("model")
                    
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
                    data=transformed_data.get("data"),
                    duration_ms=duration_ms,
                    caller_file=caller_file,
                    caller_line=caller_line,
                    caller_function=caller_function,
                    relationship_id=relationship_id
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
            
            except Exception as e:
                logger.error(f"Error processing event in batch: {str(e)}")
                # Continue with next event
                continue
        
        # Commit all changes at once
        await session.commit()
        
    except Exception as e:
        logger.error(f"Unhandled error in process_batch: {str(e)}")
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

@router.post("/", status_code=status.HTTP_202_ACCEPTED)
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

@router.post("/batch", status_code=status.HTTP_202_ACCEPTED)
async def ingest_telemetry_batch(
    background_tasks: BackgroundTasks,
    event_data_list: List[Dict[str, Any]] = Body(...),
    db_session: AsyncSession = Depends(get_session)
):
    """
    Ingest a batch of telemetry events from the monitoring SDK.
    This endpoint validates each event and queues the batch for processing.
    """
    if not event_data_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": ["No events provided"]}
        )
    
    # Validate each event in the batch
    all_errors = []
    for i, event_data in enumerate(event_data_list):
        validation_errors = validate_telemetry_event(event_data)
        if validation_errors:
            all_errors.append({"index": i, "errors": validation_errors})
    
    if all_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": all_errors}
        )
    
    # Queue the batch for asynchronous processing
    background_tasks.add_task(process_batch, event_data_list, db_session)
    
    # Return a quick acknowledgement
    return {"status": "accepted", "message": f"{len(event_data_list)} events queued for processing"} 