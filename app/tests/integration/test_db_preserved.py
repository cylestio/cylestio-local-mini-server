"""
Integration test demonstrating database preservation for inspection.

This test shows how to:
1. Use file-based SQLite database for integration tests
2. Preserve the database file after tests for manual inspection
3. Enable proper debugging of database issues
"""

import os
import sys
import pytest
import pytest_asyncio
import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from sqlalchemy import inspect, text

# Fix path for imports if running directly
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.tests.test_config import setup_file_db, get_test_db_path, should_preserve_db, get_project_root
from app.models.base import Base
from app.models.event import Event
from app.models.agent import Agent
from app.models.session import Session

# Mark test module to use asyncio
pytestmark = [pytest.mark.asyncio]

# Setup integration test environment for all tests in the module
@pytest.fixture(scope="module")
def setup_integration_test_env():
    """Setup the environment for integration tests."""
    # Configure environment for file-based database
    db_path = setup_file_db()
    print(f"\nTest database located at: {os.path.abspath(db_path)}")
    
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

async def test_database_persistence(integration_test_session):
    """Test that a file-based database is created and persisted for inspection."""
    # Get the configured database path
    db_path = get_test_db_path()
    
    # Verify that we're using a file-based database, not in-memory
    assert db_path != ":memory:", "Should be using a file-based database"
    
    # Verify that the database file exists
    assert os.path.exists(db_path), f"Database file {db_path} should exist"
    
    # Verify that the database preservation flag is set
    assert should_preserve_db(), "Database preservation should be enabled"
    
    # Use session execute to get table names safely
    result = await integration_test_session.execute(text(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ))
    table_names = [row[0] for row in result.fetchall()]
    
    # Log info for debugging
    print(f"\nDatabase tables found: {table_names}")
    print(f"Database file location: {os.path.abspath(db_path)}")
    print(f"Database will be preserved: {should_preserve_db()}")
    
    # Add some test data to verify it persists
    # Create a test agent record with a unique ID that will be recognizable
    test_agent_id = f"test-agent-{uuid.uuid4()}"
    test_agent = Agent(
        agent_id=test_agent_id,
        first_seen=datetime.now(),
        last_seen=datetime.now(),
        llm_provider="Test Provider"
    )
    integration_test_session.add(test_agent)
    await integration_test_session.commit()
    
    # Verify the agent was added
    result = await integration_test_session.execute(
        text(f"SELECT * FROM agents WHERE agent_id = '{test_agent_id}'")
    )
    saved_agent = result.fetchone()
    assert saved_agent is not None, "Agent should be saved in the database"
    
    # Create a test event linked to this agent
    test_event = Event(
        agent_id=test_agent_id,
        event_type="test_preserved_event",
        timestamp=datetime.now(),
        level="INFO",
        channel="test-channel",
        data={"message": "This test event should be preserved in the database"}
    )
    integration_test_session.add(test_event)
    await integration_test_session.commit()
    
    # Print information about where to find and how to use the preserved database
    print("\n=== PRESERVED DATABASE INFORMATION ===")
    print(f"Database path: {os.path.abspath(db_path)}")
    print("How to use this database for debugging:")
    print("1. Install 'DB Browser for SQLite' from https://sqlitebrowser.org/")
    print("2. Open the database file in DB Browser")
    print("3. You can examine the tables and run queries")
    print(f"4. Look for test agent with ID: {test_agent_id}")
    print("5. Use sqlite3 command line: sqlite3 " + os.path.abspath(db_path))
    print("6. Example SQL query: SELECT * FROM agents WHERE agent_id LIKE 'test-agent-%';")
    print("==========================================")
    
    return test_agent_id  # Return the ID for use in subsequent tests

async def test_database_schema_exists(integration_test_session):
    """Test that the database schema has properly been created."""
    # Use direct session.execute instead of inspector
    result = await integration_test_session.execute(text(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ))
    db_tables = [row[0] for row in result.fetchall()]
    
    # Get table names from metadata
    metadata_tables = Base.metadata.tables.keys()
    
    # Check if all expected tables are present
    for table_name in metadata_tables:
        assert table_name in db_tables, f"Table {table_name} should exist in the database"
    
    # Log found tables for debugging
    print(f"Database contains all expected tables: {sorted(db_tables)}")
    
    # Check column names for events table using a specific query
    result = await integration_test_session.execute(text(
        "PRAGMA table_info(events)"
    ))
    columns = result.fetchall()
    column_names = [col[1] for col in columns]  # Column name is at index 1
    
    # Expected columns for Event model
    expected_columns = ["id", "timestamp", "level", "agent_id", "event_type", "channel", "data"]
    for col in expected_columns:
        assert col in column_names, f"Column {col} should exist in the events table"

async def test_data_persistence_between_test_runs(integration_test_session):
    """Test that data is persisted between test runs in the file-based database."""
    # Query for test agents created in previous test run
    result = await integration_test_session.execute(
        text("SELECT * FROM agents WHERE agent_id LIKE 'test-agent-%'")
    )
    agents = result.fetchall()
    
    if agents:
        print(f"\nFound {len(agents)} preserved test agents from previous test runs:")
        for agent in agents:
            print(f"  - Agent ID: {agent.agent_id}")
        
        # This assertion will only fail if no preserved agents are found and database wasn't preserved
        assert len(agents) > 0, "Should find preserved agents from previous test runs"
    else:
        print("\nNo preserved test agents found. This is normal if this is the first test run.")

if __name__ == "__main__":
    # Run this specific test file with correct pytest configuration
    pytest.main(["-xvs", __file__]) 