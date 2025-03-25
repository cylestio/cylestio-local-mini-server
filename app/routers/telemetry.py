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

async def get_or_create_event(event_data, db_session):
    """Get existing event or create a new one.
    
    Ensures idempotency by checking for existing events with the same
    key attributes before creating a new one.
    
    Args:
        event_data: The event data to create
        db_session: Database session
        
    Returns:
        The existing or newly created event
    """
    # Extract identifiable fields
    agent_id = event_data.get("agent_id")
    event_type = event_data.get("event_type")
    
    # Parse timestamp if it's a string
    timestamp = event_data.get("timestamp")
    if isinstance(timestamp, str):
        timestamp = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    
    # Try to find existing event with same key data
    query = select(Event).where(
        Event.agent_id == agent_id,
        Event.event_type == event_type,
        Event.timestamp == timestamp
    )
    
    if "session_id" in event_data and event_data["session_id"]:
        query = query.where(Event.session_id == event_data["session_id"])
        
    result = await db_session.execute(query)
    existing_event = result.scalars().first()
    
    if existing_event:
        logger.info(f"Found existing event {existing_event.id}, skipping creation")
        return existing_event
    
    # Check if agent exists, create if not
    agent_result = await db_session.execute(
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
        
        db_session.add(agent)
    else:
        # Update last seen
        agent.last_seen = timestamp
    
    # Extract caller info if available
    caller_file = None
    caller_line = None
    caller_function = None
    if "caller" in event_data:
        caller = event_data["caller"]
        caller_file = caller.get("file")
        caller_line = caller.get("line")
        caller_function = caller.get("function")
    
    # Extract duration if available
    duration_ms = None
    if "data" in event_data:
        data = event_data["data"]
        if "duration_ms" in data:
            duration_ms = data["duration_ms"]
        elif "performance" in data and isinstance(data["performance"], dict) and "duration_ms" in data["performance"]:
            duration_ms = data["performance"]["duration_ms"]
    
    # Create new event
    event = Event(
        timestamp=timestamp,
        level=event_data.get("level", "INFO"),
        agent_id=agent_id,
        event_type=event_type,
        channel=event_data.get("channel"),
        direction=event_data.get("direction"),
        session_id=event_data.get("session_id"),
        data=event_data.get("data"),
        duration_ms=duration_ms,
        caller_file=caller_file,
        caller_line=caller_line,
        caller_function=caller_function
    )
    
    db_session.add(event)
    await db_session.flush()  # Get ID without committing
    
    return event

async def process_event(event_data: Dict[str, Any], session: AsyncSession):
    """
    Process a telemetry event asynchronously.
    This function handles database operations for storing the event.
    """
    try:
        # Transform the event data
        transformed_data = event_transformer.transform(event_data)
        
        # Get or create event
        event = await get_or_create_event(transformed_data, session)
        
        if not event:
            logger.error("Failed to create event")
            return
            
        # Process through business logic layer only if not already processed
        if not event.is_processed:
            try:
                # Create event processor
                event_processor = EventProcessor()
                
                # Process the event with the business logic layer
                await event_processor.process_event(event, session)
                
                logger.info(f"Event {event.id} processed through business logic layer")
            except Exception as e:
                logger.error(f"Error processing event {event.id} through business logic layer: {str(e)}")
        else:
            logger.info(f"Event {event.id} already processed, skipping business logic")
            
    except Exception as e:
        logger.error(f"Error processing event: {str(e)}")
        # Don't raise the exception - just log it

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

async def process_batch(event_data_list: List[Dict[str, Any]], db_session: AsyncSession):
    """Process a batch of events in a transaction-safe manner.
    
    Args:
        event_data_list: List of event data dictionaries
        db_session: Database session
    """
    # Transform all events first
    transformed_events = []
    for event_data in event_data_list:
        transformed = event_transformer.transform(event_data)
        transformed_events.append(transformed)
    
    # Identify relationships between events in the batch
    event_transformer._identify_relationships(transformed_events)
    
    # Process each event, ensuring idempotency
    processor = EventProcessor()
    results = []
    
    for transformed_data in transformed_events:
        try:
            # Create or get existing event
            event = await get_or_create_event(transformed_data, db_session)
            if not event:
                logger.warning(f"Failed to create event for data: {transformed_data}")
                continue
                
            # Only process if not already processed
            if not event.is_processed:
                result = await processor.process_event(event, db_session)
                if result:
                    results.append(result)
            else:
                logger.info(f"Event {event.id} already processed, skipping")
                results.append(event)
                
        except Exception as e:
            logger.error(f"Error processing event in batch: {str(e)}")
    
    return results

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
    
    # Queue the batch for asynchronous processing using the new processor
    background_tasks.add_task(process_batch, event_data_list, db_session)
    
    # Return a quick acknowledgement
    return {"status": "accepted", "message": f"{len(event_data_list)} events queued for processing"} 