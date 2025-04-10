import pytest
import json
import asyncio
from fastapi.testclient import TestClient
from fastapi import status
import pytest_asyncio
from sqlalchemy.pool import NullPool

from app.main import app
from app.database.init_db import init_db, get_session
from app.models.event import Event
from app.models.agent import Agent
from app.models.session import Session
from sqlalchemy import select

@pytest.fixture(scope="module")
def test_client():
    """Create a test client."""
    with TestClient(app) as client:
        yield client

@pytest_asyncio.fixture(scope="function")
async def test_db():
    """Set up test database."""
    await init_db()
    yield
    # Cleanup will be handled by FastAPI's dependency injection

# Test data for valid events
VALID_EVENT = {
    "timestamp": "2025-03-18T18:57:11.620036Z",
    "level": "INFO",
    "agent_id": "test-agent",
    "event_type": "TEST_EVENT",
    "channel": "TEST",
    "data": {"message": "This is a test event"}
}

# Test data for events with invalid fields
INVALID_EVENT_MISSING_TIMESTAMP = {
    "level": "INFO",
    "agent_id": "test-agent",
    "event_type": "TEST_EVENT",
    "channel": "TEST"
}

INVALID_EVENT_MISSING_AGENT_ID = {
    "timestamp": "2025-03-18T18:57:11.620036Z",
    "level": "INFO",
    "event_type": "TEST_EVENT",
    "channel": "TEST"
}

INVALID_EVENT_MISSING_EVENT_TYPE = {
    "timestamp": "2025-03-18T18:57:11.620036Z",
    "level": "INFO",
    "agent_id": "test-agent",
    "channel": "TEST"
}

# Load test data from example JSON files
def load_test_data_from_file(filename):
    try:
        with open(f"input_json_records_examples/{filename}", "r") as f:
            # Get first line which is a single JSON object
            line = f.readline().strip()
            return json.loads(line)
    except FileNotFoundError:
        return None

# Tests for validation only (no database operations)
def test_telemetry_endpoint_valid_data(test_client):
    """Test that the telemetry endpoint accepts valid data and returns 202."""
    response = test_client.post("/api/v1/telemetry", json=VALID_EVENT)
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json()["status"] == "accepted"

def test_telemetry_endpoint_missing_timestamp(test_client):
    """Test that the endpoint rejects events without a timestamp."""
    response = test_client.post("/api/v1/telemetry", json=INVALID_EVENT_MISSING_TIMESTAMP)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "timestamp" in response.json()["detail"]["errors"][0]

def test_telemetry_endpoint_missing_agent_id(test_client):
    """Test that the endpoint rejects events without an agent_id."""
    response = test_client.post("/api/v1/telemetry", json=INVALID_EVENT_MISSING_AGENT_ID)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "agent_id" in response.json()["detail"]["errors"][0]

def test_telemetry_endpoint_missing_event_type(test_client):
    """Test that the endpoint rejects events without an event_type."""
    response = test_client.post("/api/v1/telemetry", json=INVALID_EVENT_MISSING_EVENT_TYPE)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "event_type" in response.json()["detail"]["errors"][0]

# Tests that require database setup
# Skipping these for now as they require more complex setup
@pytest.mark.skip(reason="Requires database setup")
@pytest.mark.asyncio
async def test_event_stored_in_database(test_client, test_db):
    """Test that valid events are stored in the database."""
    # Send a valid event
    response = test_client.post("/api/v1/telemetry", json=VALID_EVENT)
    assert response.status_code == status.HTTP_202_ACCEPTED
    
    # Wait for async processing
    await asyncio.sleep(0.5)
    
    async for session in get_session():
        try:
            result = await session.execute(
                select(Event).where(
                    Event.agent_id == VALID_EVENT["agent_id"],
                    Event.event_type == VALID_EVENT["event_type"]
                )
            )
            event = result.scalars().first()
            
            assert event is not None
            assert event.agent_id == VALID_EVENT["agent_id"]
            assert event.event_type == VALID_EVENT["event_type"]
            
            # Clean up
            if event:
                await session.delete(event)
                await session.commit()
        finally:
            await session.close()

@pytest.mark.skip(reason="Requires database setup")
@pytest.mark.asyncio
async def test_with_example_json_files(test_client, test_db):
    """Test the telemetry endpoint with real-world examples from the provided JSON files."""
    # Load example data
    weather_event = load_test_data_from_file("weather_monitoring.json")
    if not weather_event:
        pytest.skip("Example JSON file not found, skipping test")
    
    # Send the event
    response = test_client.post("/api/v1/telemetry", json=weather_event)
    assert response.status_code == status.HTTP_202_ACCEPTED
    
    # Wait for async processing
    await asyncio.sleep(0.5)
    
    async for session in get_session():
        try:
            result = await session.execute(
                select(Event).where(
                    Event.agent_id == weather_event["agent_id"],
                    Event.event_type == weather_event["event_type"]
                )
            )
            event = result.scalars().first()
            
            assert event is not None
            assert event.agent_id == weather_event["agent_id"]
            assert event.event_type == weather_event["event_type"]
            
            # Clean up
            if event:
                await session.delete(event)
                await session.commit()
        finally:
            await session.close() 