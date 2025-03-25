#!/usr/bin/env python
"""
Test script for token usage extraction.

This script loads example records from the resources directory and tests
the token usage extractors to ensure they correctly extract data.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
import datetime

# Add parent directory to path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.init_db import init_db, get_session, engine, async_session
from app.models.event import Event
from app.models.agent import Agent
from app.models.token_usage import TokenUsage
from app.business_logic.extractors.token_usage_extractor import TokenUsageExtractor
from app.business_logic.extractors.model_response_extractor import ModelResponseExtractor
from app.business_logic.extractors.llm_call_extractor import LLMCallExtractor
from sqlalchemy import select, func

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

async def load_example_records():
    """Load example records from the resources directory."""
    example_path = os.path.join("resources", "example_input_json_records", "example_input_json_records.json")
    
    records = []
    with open(example_path, 'r') as f:
        # The file should contain an array of JSON objects
        try:
            # Try to load the file as a single JSON array
            array_data = json.load(f)
            if isinstance(array_data, list):
                records = array_data
            else:
                logger.error(f"Unexpected format: not a JSON array")
        except json.JSONDecodeError:
            # If not a single JSON array, try parsing line by line
            f.seek(0)  # Reset file pointer
            for line in f:
                if line.strip():  # Skip empty lines
                    try:
                        record = json.loads(line.strip())
                        records.append(record)
                    except json.JSONDecodeError as e:
                        logger.error(f"Error parsing JSON: {e}")
    
    return records

async def create_event(event_data, db_session):
    """Create an event from event data."""
    # Extract required fields
    timestamp = event_data.get("timestamp")
    level = event_data.get("level", "INFO")
    agent_id = event_data.get("agent_id")
    event_type = event_data.get("event_type")
    channel = event_data.get("channel", "UNKNOWN")
    
    # Convert timestamp to datetime if it's a string
    if isinstance(timestamp, str):
        timestamp = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    
    # Create or get agent
    result = await db_session.execute(
        select(Agent).where(Agent.agent_id == agent_id)
    )
    agent = result.scalars().first()
    
    if not agent:
        agent = Agent(agent_id=agent_id)
        db_session.add(agent)
    
    # Create event
    event = Event(
        timestamp=timestamp,
        level=level,
        agent_id=agent_id,
        event_type=event_type,
        channel=channel,
        direction=event_data.get("direction"),
        session_id=event_data.get("session_id"),
        data=event_data.get("data"),
    )
    
    db_session.add(event)
    await db_session.flush()
    
    return event

async def test_extractors():
    """Test token usage extraction from example records."""
    # Initialize database
    await init_db()
    
    # Create extractors
    token_extractor = TokenUsageExtractor()
    model_response_extractor = ModelResponseExtractor()
    llm_call_extractor = LLMCallExtractor()
    
    # Load example records
    records = await load_example_records()
    logger.info(f"Loaded {len(records)} example records")
    
    # Process records through extractors
    async with async_session() as session:
        # Import records
        events = []
        for record in records:
            event = await create_event(record, session)
            events.append(event)
        
        logger.info(f"Created {len(events)} events")
        
        # Extract token usage
        token_count = 0
        model_response_count = 0
        llm_call_count = 0
        
        for event in events:
            # Apply each extractor without filtering by event type
            # Try token extractor on all events
            if token_extractor.can_process(event):
                await token_extractor.process(event, session)
                token_count += 1
            
            # Try model response extractor on all events
            if model_response_extractor.can_process(event):
                await model_response_extractor.process(event, session)
                model_response_count += 1
                
            # Try LLM call extractor on all events
            if llm_call_extractor.can_process(event):
                await llm_call_extractor.process(event, session)
                llm_call_count += 1
        
        # Commit changes
        await session.commit()
        
        # Verify token usage records
        result = await session.execute(select(func.count()).select_from(TokenUsage))
        token_usage_count = result.scalar()
        
        # Get statistics
        result = await session.execute(
            select(
                func.sum(TokenUsage.input_tokens),
                func.sum(TokenUsage.output_tokens),
                func.sum(TokenUsage.total_tokens)
            )
        )
        total_input, total_output, total_tokens = result.first()
        
        # Print results
        logger.info(f"Processed events with token_extractor: {token_count}")
        logger.info(f"Processed events with model_response_extractor: {model_response_count}")
        logger.info(f"Processed events with llm_call_extractor: {llm_call_count}")
        logger.info(f"Created {token_usage_count} token usage records")
        logger.info(f"Total input tokens: {total_input}")
        logger.info(f"Total output tokens: {total_output}")
        logger.info(f"Total tokens: {total_tokens}")
        
        # List models and their token counts
        result = await session.execute(
            select(
                TokenUsage.model,
                func.count(),
                func.sum(TokenUsage.input_tokens),
                func.sum(TokenUsage.output_tokens)
            ).group_by(TokenUsage.model)
        )
        
        logger.info("Token usage by model:")
        for model, count, input_tokens, output_tokens in result:
            if model:
                logger.info(f"  {model}: {count} records, {input_tokens} input, {output_tokens} output")
            else:
                logger.info(f"  Unknown model: {count} records, {input_tokens} input, {output_tokens} output")

async def main():
    """Main function to run the test script."""
    await test_extractors()

if __name__ == "__main__":
    asyncio.run(main()) 