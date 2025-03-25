#!/usr/bin/env python
"""
Test script to verify the improved event processing with duplicate prevention.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone

# Add parent directory to path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.init_db import init_db, get_session, engine, async_session
from app.models.event import Event
from app.models.agent import Agent
from app.models.content_analysis import ContentAnalysis
from app.models.performance_metric import PerformanceMetric
from app.models.model_details import ModelDetails
from app.routers.telemetry import process_batch
from sqlalchemy import select, func

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

async def load_test_events():
    """Load test events from example JSON file."""
    example_path = os.path.join("resources", "example_input_json_records", "example_input_json_records.json")
    
    with open(example_path, "r") as f:
        return json.load(f)

async def count_records(db):
    """Count records in key tables to check for duplicates."""
    tables = {
        "events": Event,
        "content_analysis": ContentAnalysis,
        "performance_metrics": PerformanceMetric,
        "model_details": ModelDetails,
    }
    
    results = {}
    for name, table in tables.items():
        result = await db.execute(select(func.count()).select_from(table))
        count = result.scalar()
        results[name] = count
        
    return results

async def test_duplicate_prevention():
    """Test that duplicate events are properly prevented."""
    # Initialize the database
    await init_db()
    
    # Load test events
    events = await load_test_events()
    logger.info(f"Loaded {len(events)} test events")
    
    # Process first batch
    logger.info("Processing first batch...")
    async with async_session() as db:
        await process_batch(events, db)
    
    # Get record counts after first batch
    async with async_session() as db:
        counts1 = await count_records(db)
    
    logger.info(f"After first batch: {counts1}")
    
    # Process the same batch again
    logger.info("Processing DUPLICATE batch...")
    async with async_session() as db:
        await process_batch(events, db)
    
    # Get record counts after second batch
    async with async_session() as db:
        counts2 = await count_records(db)
    
    logger.info(f"After second batch: {counts2}")
    
    # Check if counts are the same (no duplicates)
    if counts1 == counts2:
        logger.info("TEST PASSED: No duplicates created!")
    else:
        logger.error("TEST FAILED: Duplicates were created.")
        for table, count in counts1.items():
            if count != counts2[table]:
                logger.error(f"Table {table}: {count} -> {counts2[table]}")

if __name__ == "__main__":
    asyncio.run(test_duplicate_prevention()) 