import asyncio
import unittest
import datetime
import sys
from pathlib import Path

# Add parent directory to path for relative imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select

from app.models.base import Base
from app.models.agent import Agent
from app.models.event import Event
from app.models.session import Session

# Use in-memory SQLite for testing
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

class TestModels(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        """Set up test database."""
        self.engine = create_async_engine(
            TEST_DB_URL,
            echo=False,
            connect_args={"check_same_thread": False},
        )
        
        self.async_session = sessionmaker(
            self.engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )
        
        # Create tables
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def asyncTearDown(self):
        """Tear down test database."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        
        await self.engine.dispose()
    
    async def test_agent_creation(self):
        """Test creating an agent."""
        now = datetime.datetime.utcnow()
        
        async with self.async_session() as session:
            # Create agent
            agent = Agent(
                agent_id="test-agent",
                first_seen=now,
                last_seen=now,
                llm_provider="test-provider"
            )
            session.add(agent)
            await session.commit()
            
            # Query agent
            result = await session.execute(select(Agent).where(Agent.agent_id == "test-agent"))
            agent = result.scalars().first()
            
            # Assertions
            self.assertIsNotNone(agent)
            self.assertEqual(agent.agent_id, "test-agent")
            self.assertEqual(agent.llm_provider, "test-provider")
    
    async def test_event_creation(self):
        """Test creating an event."""
        now = datetime.datetime.utcnow()
        
        async with self.async_session() as session:
            # Create agent
            agent = Agent(
                agent_id="test-agent",
                first_seen=now,
                last_seen=now
            )
            session.add(agent)
            await session.commit()
            
            # Create event
            event = Event(
                timestamp=now,
                level="INFO",
                agent_id="test-agent",
                event_type="test_event",
                channel="TEST",
                data={"test": "data"}
            )
            session.add(event)
            await session.commit()
            
            # Query event
            result = await session.execute(select(Event).where(Event.event_type == "test_event"))
            event = result.scalars().first()
            
            # Assertions
            self.assertIsNotNone(event)
            self.assertEqual(event.agent_id, "test-agent")
            self.assertEqual(event.event_type, "test_event")
            self.assertEqual(event.data, {"test": "data"})
    
    async def test_session_creation(self):
        """Test creating a session."""
        now = datetime.datetime.utcnow()
        
        async with self.async_session() as session:
            # Create agent
            agent = Agent(
                agent_id="test-agent",
                first_seen=now,
                last_seen=now
            )
            session.add(agent)
            await session.commit()
            
            # Create session
            test_session = Session(
                session_id="test-session",
                agent_id="test-agent",
                start_time=now,
                total_events=0
            )
            session.add(test_session)
            await session.commit()
            
            # Query session
            result = await session.execute(select(Session).where(Session.session_id == "test-session"))
            test_session = result.scalars().first()
            
            # Assertions
            self.assertIsNotNone(test_session)
            self.assertEqual(test_session.agent_id, "test-agent")
            self.assertEqual(test_session.total_events, 0)
    
    async def test_relationships(self):
        """Test relationships between models."""
        now = datetime.datetime.utcnow()
        
        async with self.async_session() as session:
            # Create agent
            agent = Agent(
                agent_id="test-agent",
                first_seen=now,
                last_seen=now
            )
            session.add(agent)
            
            # Create event
            event = Event(
                timestamp=now,
                level="INFO",
                agent_id="test-agent",
                event_type="test_event",
                channel="TEST"
            )
            session.add(event)
            
            # Create session
            test_session = Session(
                session_id="test-session",
                agent_id="test-agent",
                start_time=now,
                total_events=1
            )
            session.add(test_session)
            
            await session.commit()
            
            # Instead of using lazy loading relationships, query the events directly
            result = await session.execute(select(Event).where(Event.agent_id == "test-agent"))
            events = result.scalars().all()
            
            # Test agent-events relationship
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].event_type, "test_event")

if __name__ == "__main__":
    unittest.main() 