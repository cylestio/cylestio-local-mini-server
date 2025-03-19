#!/usr/bin/env python3
"""
Verification script for the telemetry API.
This script sends sample events from the example JSON files and verifies they are stored correctly.
"""

import asyncio
import aiohttp
import json
import sys
import os
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Adjust the path to be able to import from the app directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.models.event import Event
from app.models.agent import Agent

# Local server URL
API_URL = "http://localhost:8000/api/v1/telemetry"

# Database connection
DB_PATH = os.environ.get("CYLESTIO_DB_PATH", "./data/cylestio.db")
SQLALCHEMY_DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL, 
    echo=False,
    connect_args={"check_same_thread": False},
)

async_session = sessionmaker(
    engine, 
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db_session():
    """Get a database session."""
    async with async_session() as session:
        yield session

async def load_json_records(filename):
    """Load JSON records from file, one per line."""
    filepath = os.path.join("input_json_records_examples", filename)
    records = []
    
    try:
        with open(filepath, 'r') as f:
            for line in f:
                if line.strip():  # Skip empty lines
                    records.append(json.loads(line))
    except FileNotFoundError:
        print(f"Warning: File not found: {filepath}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON in {filepath}: {e}")
    
    return records

async def send_event(session, event):
    """Send a single event to the telemetry API."""
    try:
        async with session.post(API_URL, json=event) as response:
            response_data = await response.json()
            status = response.status
            return status, response_data
    except Exception as e:
        return None, str(e)

async def verify_event_in_database(event):
    """Verify that an event has been stored in the database."""
    async for session in get_db_session():
        try:
            result = await session.execute(
                select(Event).where(
                    Event.agent_id == event["agent_id"],
                    Event.event_type == event["event_type"]
                ).order_by(Event.id.desc()).limit(1)
            )
            db_event = result.scalars().first()
            
            if db_event:
                print(f"✓ Event {event['event_type']} for agent {event['agent_id']} found in database")
                return True
            else:
                print(f"✗ Event {event['event_type']} for agent {event['agent_id']} NOT found in database")
                return False
        except Exception as e:
            print(f"Error verifying event in database: {e}")
            return False

async def test_invalid_events(session):
    """Test various invalid events to ensure proper error handling."""
    print("\n--- Testing invalid events ---")
    
    # Test missing timestamp
    event_missing_timestamp = {
        "agent_id": "test-agent",
        "event_type": "TEST_EVENT"
    }
    status, response = await send_event(session, event_missing_timestamp)
    print(f"Missing timestamp: Status {status}, {'Error detected correctly' if status == 400 else 'ERROR: Should have failed'}")
    
    # Test missing agent_id
    event_missing_agent_id = {
        "timestamp": "2025-03-18T18:57:11.620036Z",
        "event_type": "TEST_EVENT"
    }
    status, response = await send_event(session, event_missing_agent_id)
    print(f"Missing agent_id: Status {status}, {'Error detected correctly' if status == 400 else 'ERROR: Should have failed'}")
    
    # Test missing event_type
    event_missing_event_type = {
        "timestamp": "2025-03-18T18:57:11.620036Z",
        "agent_id": "test-agent"
    }
    status, response = await send_event(session, event_missing_event_type)
    print(f"Missing event_type: Status {status}, {'Error detected correctly' if status == 400 else 'ERROR: Should have failed'}")

async def main():
    """Main function to test the telemetry API."""
    print("=== Cylestio Mini-Local Server: Telemetry API Verification ===")
    
    # List of example files to test
    example_files = ["weather_monitoring.json", "rag_monitoring.json", "chatbot_monitoring.json"]
    
    # Create aiohttp session
    async with aiohttp.ClientSession() as session:
        # Test with example files
        for filename in example_files:
            print(f"\n--- Testing with {filename} ---")
            records = await load_json_records(filename)
            
            if not records:
                print(f"No records found in {filename}, skipping...")
                continue
            
            # Test with a subset of records (first 3)
            for i, event in enumerate(records[:3]):
                print(f"Sending event {i+1}/{min(3, len(records))}: {event['event_type']}")
                status, response = await send_event(session, event)
                
                if status == 202:
                    print(f"✓ Event accepted with status {status}")
                    # Allow time for async processing
                    await asyncio.sleep(0.5)
                    # Verify the event was stored
                    await verify_event_in_database(event)
                else:
                    print(f"✗ Failed to send event: Status {status}, Response: {response}")
        
        # Test invalid events
        await test_invalid_events(session)
    
    print("\n=== Verification Complete ===")

if __name__ == "__main__":
    asyncio.run(main()) 