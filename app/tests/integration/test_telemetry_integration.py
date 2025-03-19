import os
import sys
import pytest
import pytest_asyncio
import asyncio
import json
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import shutil
from pathlib import Path
from sqlalchemy import text

# Add the parent directory to sys.path to import the app
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.main import app
from app.models.base import Base
from app.models.event import Event
from app.models.agent import Agent
from app.models.session import Session
from app.tests.test_config import setup_file_db, get_test_db_path, get_project_root, should_preserve_db

# Mark all tests as asyncio
pytestmark = pytest.mark.asyncio

# Load example telemetry records
EXAMPLE_RECORDS_PATH = os.path.join(get_project_root(), "resources/example_input_json_records/example_records.json")

def load_example_records():
    """Load example telemetry records from JSON file."""
    with open(EXAMPLE_RECORDS_PATH, "r") as f:
        # Each line is a separate JSON object
        return [json.loads(line) for line in f.readlines() if line.strip()]

# Setup integration test environment for all tests in the module
@pytest.fixture(scope="module")
def setup_integration_test_env():
    """Setup the environment for integration tests."""
    # Configure environment for file-based database
    db_path = setup_file_db(preserve_db=True)
    print(f"Using preserved test database at: {db_path}")
    
    # Create test engine with absolute path
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    
    # Ensure the path is absolute
    if not os.path.isabs(db_path) and db_path != ":memory:":
        db_path = os.path.join(get_project_root(), db_path)
    
    # Create engine for this test module
    test_engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        echo=False,
        connect_args={"check_same_thread": False},
        future=True
    )
    
    # Session factory for file-based tests
    TestingSessionLocal = sessionmaker(
        test_engine, 
        expire_on_commit=False, 
        class_=AsyncSession
    )
    
    # Store engine and session factory
    setup_integration_test_env.engine = test_engine
    setup_integration_test_env.session_factory = TestingSessionLocal
    
    yield setup_integration_test_env
    
    # Don't cleanup - we want to preserve the database

# Initialize database tables
@pytest_asyncio.fixture(scope="module")
async def setup_integration_test_db(setup_integration_test_env):
    """Setup the database for integration tests."""
    engine = setup_integration_test_env.engine
    
    # Create tables
    async with engine.begin() as conn:
        # Only drop tables if we're not preserving the database
        if not should_preserve_db():
            await conn.run_sync(Base.metadata.drop_all)
        
        # Create tables if they don't exist
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Don't drop tables when preserving database

# Session for tests
@pytest_asyncio.fixture(scope="function")
async def integration_test_session(setup_integration_test_db, setup_integration_test_env):
    """Create a session for integration tests."""
    SessionLocal = setup_integration_test_env.session_factory
    async with SessionLocal() as session:
        yield session
        await session.commit()

async def test_ingest_single_telemetry_event(setup_integration_test_env, integration_test_client, integration_test_session):
    """Test ingesting a single telemetry event."""
    # Load example records
    example_records = load_example_records()
    
    # Use the first record
    test_record = example_records[0]
    
    # Get the existing event count before we start to identify our newly added event
    result = await integration_test_session.execute(text("SELECT COUNT(*) FROM events"))
    initial_count = result.scalar() or 0
    
    # Send to the API
    response = integration_test_client.post("/api/v1/telemetry", json=test_record)
    
    # Check response
    assert response.status_code == 202, f"Expected 202, got {response.status_code}: {response.text}"
    
    # Wait for background processing to complete
    await asyncio.sleep(1)
    
    # Verify the event was stored in the database
    result = await integration_test_session.execute(text("SELECT COUNT(*) FROM events"))
    current_count = result.scalar()
    assert current_count > initial_count, f"Expected more than {initial_count} events, but found {current_count}"
    
    # Get the most recently added event assuming ascending ids
    result = await integration_test_session.execute(text(
        "SELECT * FROM events ORDER BY id DESC LIMIT 1"
    ))
    event = result.fetchone()
    assert event is not None, "Could not retrieve event from database"
    
    # Verify the event matches what we sent
    assert event.event_type == test_record["event_type"], f"Event type mismatch: {event.event_type} vs {test_record['event_type']}"
    assert event.agent_id == test_record["agent_id"], f"Agent ID mismatch: {event.agent_id} vs {test_record['agent_id']}"
    
    print(f"Successfully added a new event with type {event.event_type}")

async def test_ingest_telemetry_batch(setup_integration_test_env, integration_test_client, integration_test_session):
    """Test ingesting a batch of telemetry events."""
    # Load example records
    example_records = load_example_records()
    
    # Use the first few records for the batch
    test_batch = example_records[:3]
    
    # Send to the API
    response = integration_test_client.post("/api/v1/telemetry/batch", json=test_batch)
    
    # Check response
    assert response.status_code == 202, f"Expected 202, got {response.status_code}: {response.text}"
    
    # Wait for background processing to complete
    await asyncio.sleep(2)
    
    # Verify the events were stored in the database
    result = await integration_test_session.execute(text("SELECT COUNT(*) FROM events"))
    count = result.scalar()
    assert count >= 3, f"Expected at least 3 events, found {count}"

async def test_query_events_by_agent(setup_integration_test_env, integration_test_client, integration_test_session):
    """Test querying events by agent ID."""
    # Load example records
    example_records = load_example_records()
    
    # Find a unique agent ID from the example records
    agent_id = example_records[0]["agent_id"]
    
    # Query events for this agent - use the correct API endpoint
    response = integration_test_client.get(f"/api/v1/agents/{agent_id}/events")
    
    # Check response
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    # Verify the response contains events
    data = response.json()
    assert "results" in data, "Response does not contain events"

async def test_end_to_end_flow(setup_integration_test_env, integration_test_client, integration_test_session):
    """Test the complete end-to-end flow."""
    # Load example records
    example_records = load_example_records()
    
    # Clear existing data for clean test
    await integration_test_session.execute(text("DELETE FROM events"))
    await integration_test_session.execute(text("DELETE FROM agents"))
    await integration_test_session.commit()
    
    # Step 1: Ingest each telemetry event one by one
    for index, record in enumerate(example_records):
        response = integration_test_client.post("/api/v1/telemetry", json=record)
        assert response.status_code == 202, f"Failed to ingest record {index}: {response.status_code} - {response.text}"
        
        # Small delay to avoid overwhelming the server
        await asyncio.sleep(0.1)
    
    # Step 2: Wait for background processing to complete
    await asyncio.sleep(3)
    
    # Step 3: Verify all events were stored
    result = await integration_test_session.execute(text("SELECT COUNT(*) FROM events"))
    count = result.scalar()
    assert count == len(example_records), f"Expected {len(example_records)} events, found {count}"
    
    # Get unique agent IDs from example records
    agent_ids = set(record["agent_id"] for record in example_records)
    
    # Step 4: Query for each agent
    for agent_id in agent_ids:
        response = integration_test_client.get(f"/api/v1/agents/{agent_id}/events")
        assert response.status_code == 200, f"Failed to query events for agent {agent_id}"
        
        data = response.json()
        assert "results" in data, f"Response for agent {agent_id} does not contain events"
    
    print(f"Successfully stored {count} events in the preserved database at {get_test_db_path()}")
    print(f"You can inspect this database using a SQLite browser")

if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 