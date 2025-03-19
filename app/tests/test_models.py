import asyncio
import unittest
import datetime
import sys
import logging
import os
from pathlib import Path
import pytest
import pytest_asyncio
from sqlalchemy.util import greenlet_spawn
from sqlalchemy import select, inspect, text

# Add parent directory to path for relative imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import models
from app.models.base import Base
from app.models.agent import Agent
from app.models.event import Event
from app.models.session import Session

# Import database utilities
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use a test-specific database
# Using file-based SQLite instead of in-memory to avoid transaction issues
TEST_DB_DIR = "./test_data"
TEST_DB_PATH = f"{TEST_DB_DIR}/test_db.sqlite"

# Create test directory if it doesn't exist
os.makedirs(TEST_DB_DIR, exist_ok=True)

# Remove existing test database if it exists
if os.path.exists(TEST_DB_PATH):
    try:
        os.remove(TEST_DB_PATH)
        logger.info(f"Removed existing test database at {TEST_DB_PATH}")
    except Exception as e:
        logger.error(f"Failed to remove existing test database: {e}")

# Create SQLite async engine specifically for tests
TEST_DB_URL = f"sqlite+aiosqlite:///{TEST_DB_PATH}"
test_engine = create_async_engine(
    TEST_DB_URL,
    echo=True,
    connect_args={"check_same_thread": False},
)

# Create async session factory
test_async_session = sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_database():
    """Initialize the test database once for all tests."""
    logger.info("Creating database tables for all tests...")
    
    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # Log the tables created
        def get_table_names(connection):
            inspector = inspect(connection)
            return inspector.get_table_names()
        table_names = await conn.run_sync(get_table_names)
        logger.info(f"Created tables: {table_names}")
    
    yield
    
    # Clean up after all tests
    logger.info("Cleaning up test database...")
    
    # Close all connections and dispose of the engine
    await test_engine.dispose()
    
    # Optionally delete the test database file
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
            logger.info(f"Removed test database at {TEST_DB_PATH}")
        except Exception as e:
            logger.error(f"Failed to remove test database: {e}")

@pytest_asyncio.fixture
async def db_session():
    """Create a database session for a test."""
    logger.info("Creating session for test...")
    
    # Create tables first if they don't exist
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # Log the tables available
        def get_table_names(connection):
            inspector = inspect(connection)
            return inspector.get_table_names()
        table_names = await conn.run_sync(get_table_names)
        logger.info(f"Tables available: {table_names}")
    
    # Start a fresh session for each test
    async with test_async_session() as session:
        # Clean existing data
        async with session.begin():
            if 'events' in table_names:
                await session.execute(text("DELETE FROM events"))
            if 'sessions' in table_names:
                await session.execute(text("DELETE FROM sessions"))
            if 'agents' in table_names:
                await session.execute(text("DELETE FROM agents"))
        
        # Yield the session for the test to use
        yield session

@pytest.mark.asyncio
async def test_agent_creation(db_session: AsyncSession):
    """Test creating an agent."""
    # Start a new transaction
    async with db_session.begin():
        # Create a test agent
        agent = Agent(
            agent_id="test-agent",
            first_seen=datetime.datetime.now(datetime.UTC),
            last_seen=datetime.datetime.now(datetime.UTC)
        )
        db_session.add(agent)
    
    # Start a new transaction for the query
    async with db_session.begin():
        # Query the agent
        result = await db_session.execute(
            select(Agent).where(Agent.agent_id == "test-agent")
        )
        saved_agent = result.scalars().first()
        
        # Verify the agent was saved correctly
        assert saved_agent is not None
        assert saved_agent.agent_id == "test-agent"

@pytest.mark.asyncio
async def test_event_creation(db_session: AsyncSession):
    """Test creating an event."""
    # Create an agent and an event in a single transaction
    async with db_session.begin():
        # First create an agent (required by foreign key constraint)
        agent = Agent(
            agent_id="test-agent",
            first_seen=datetime.datetime.now(datetime.UTC),
            last_seen=datetime.datetime.now(datetime.UTC)
        )
        db_session.add(agent)
        
        # Create a test event
        event = Event(
            timestamp=datetime.datetime.now(datetime.UTC),
            level="INFO",
            agent_id="test-agent",
            event_type="test_event",
            channel="test_channel"
        )
        db_session.add(event)
    
    # Query in a new transaction
    async with db_session.begin():
        # Query the event
        result = await db_session.execute(
            select(Event).where(Event.event_type == "test_event")
        )
        saved_event = result.scalars().first()
        
        # Verify the event was saved correctly
        assert saved_event is not None
        assert saved_event.event_type == "test_event"
        assert saved_event.agent_id == "test-agent"

@pytest.mark.asyncio
async def test_session_creation(db_session: AsyncSession):
    """Test creating a session."""
    # Create an agent and a session in a single transaction
    async with db_session.begin():
        # First create an agent (required by foreign key constraint)
        agent = Agent(
            agent_id="test-agent",
            first_seen=datetime.datetime.now(datetime.UTC),
            last_seen=datetime.datetime.now(datetime.UTC)
        )
        db_session.add(agent)
        
        # Create a test session
        test_session = Session(
            session_id="test-session",
            agent_id="test-agent",
            start_time=datetime.datetime.now(datetime.UTC),
            total_events=1
        )
        db_session.add(test_session)
    
    # Query in a new transaction
    async with db_session.begin():
        # Query the session
        result = await db_session.execute(
            select(Session).where(Session.session_id == "test-session")
        )
        saved_session = result.scalars().first()
        
        # Verify the session was saved correctly
        assert saved_session is not None
        assert saved_session.session_id == "test-session"
        assert saved_session.agent_id == "test-agent"

@pytest.mark.asyncio
async def test_relationships(db_session: AsyncSession):
    """Test relationships between models."""
    # Create an agent and an event in a single transaction
    async with db_session.begin():
        # Create a test agent
        agent = Agent(
            agent_id="test-agent",
            first_seen=datetime.datetime.now(datetime.UTC),
            last_seen=datetime.datetime.now(datetime.UTC)
        )
        db_session.add(agent)
        
        # Create a test event for the agent
        event = Event(
            timestamp=datetime.datetime.now(datetime.UTC),
            level="INFO",
            agent_id="test-agent",
            event_type="test_event",
            channel="test_channel"
        )
        db_session.add(event)
    
    # Query in a new transaction
    async with db_session.begin():
        # Query the agent with its events
        result = await db_session.execute(
            select(Agent).where(Agent.agent_id == "test-agent")
        )
        saved_agent = result.scalars().first()
        
        # Verify the relationship using greenlet_spawn for lazy loading
        def get_events():
            return len(saved_agent.events)
        
        event_count = await greenlet_spawn(get_events)
        assert event_count == 1
        
        def get_event_type():
            return saved_agent.events[0].event_type
            
        event_type = await greenlet_spawn(get_event_type)
        assert event_type == "test_event"

if __name__ == "__main__":
    unittest.main() 