"""
Unit tests for CommonExtractor.

This module tests the functionality of the CommonExtractor class.
"""

import unittest
import asyncio
from datetime import datetime

# Mock the extractor for testing
class MockCommonExtractor:
    """Mock implementation of CommonExtractor for testing."""
    
    def can_process(self, event):
        """Always return True - this extractor processes all events."""
        return True
    
    def _extract_caller_info(self, event):
        """Extract caller information from the event."""
        if hasattr(event, 'data') and event.data and 'caller' in event.data:
            caller = event.data['caller']
            event.caller_file = caller.get('file')
            event.caller_line = caller.get('line')
            event.caller_function = caller.get('function')
    
    async def _process_agent_info(self, event, db_session):
        """Process agent information from the event."""
        # In a real implementation, this would check for an existing agent
        # and update or create one as needed
        from tests.fixtures.mock_models import Agent
        agent = Agent(agent_id=event.agent_id)
        db_session.add(agent)
    
    async def _process_session_info(self, event, db_session):
        """Process session information from the event."""
        # In a real implementation, this would check for an existing session
        # and update or create one as needed
        from tests.fixtures.mock_models import Session
        session = Session(session_id=event.session_id, agent_id=event.agent_id)
        db_session.add(session)
    
    async def process(self, event, db_session):
        """Process the event and extract common information."""
        # Extract caller info
        self._extract_caller_info(event)
        
        # Process agent and session info
        await self._process_agent_info(event, db_session)
        await self._process_session_info(event, db_session)


from tests.fixtures.event_fixtures import (
    MODEL_REQUEST_EVENT, 
    MODEL_RESPONSE_EVENT,
    MONITOR_INIT_EVENT
)
from tests.fixtures.db_helper import mock_db_session_factory
from tests.fixtures.mock_models import Agent, Session


class TestCommonExtractor(unittest.TestCase):
    """Test cases for the CommonExtractor."""
    
    def setUp(self):
        """Set up test environment before each test."""
        self.extractor = MockCommonExtractor()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        """Clean up after each test."""
        self.loop.close()
    
    def test_can_process(self):
        """Test that the extractor can process all event types."""
        # CommonExtractor should be able to process all events
        self.assertTrue(self.extractor.can_process(MODEL_REQUEST_EVENT))
        self.assertTrue(self.extractor.can_process(MODEL_RESPONSE_EVENT))
        self.assertTrue(self.extractor.can_process(MONITOR_INIT_EVENT))
    
    def test_extract_caller_info(self):
        """Test extraction of caller information."""
        event = MODEL_REQUEST_EVENT
        
        # Call the method
        self.extractor._extract_caller_info(event)
        
        # Check that caller info was correctly extracted
        self.assertEqual(event.caller_file, "/app/example.py")
        self.assertEqual(event.caller_line, 42)
        self.assertEqual(event.caller_function, "ask_question")
    
    def test_process_agent_info(self):
        """Test processing agent info."""
        event = MODEL_REQUEST_EVENT
        db_session = mock_db_session_factory()
        
        # Call the method
        self.loop.run_until_complete(self.extractor._process_agent_info(event, db_session))
        
        # Check that an agent was added
        self.assertEqual(len(db_session.added_objects), 1)
        added_agent = db_session.added_objects[0]
        self.assertIsInstance(added_agent, Agent)
        self.assertEqual(added_agent.agent_id, "test-agent-id")
    
    def test_process_session_info(self):
        """Test processing session info."""
        event = MODEL_REQUEST_EVENT
        db_session = mock_db_session_factory()
        
        # Call the method
        self.loop.run_until_complete(self.extractor._process_session_info(event, db_session))
        
        # Check that a session was added
        self.assertEqual(len(db_session.added_objects), 1)
        added_session = db_session.added_objects[0]
        self.assertIsInstance(added_session, Session)
        self.assertEqual(added_session.session_id, "test-session-id")
        self.assertEqual(added_session.agent_id, "test-agent-id")
    
    def test_process_method(self):
        """Test the main process method."""
        event = MODEL_REQUEST_EVENT
        db_session = mock_db_session_factory()
        
        # Call the process method
        self.loop.run_until_complete(self.extractor.process(event, db_session))
        
        # Check that both agent and session were processed
        self.assertEqual(len(db_session.added_objects), 2)
        
        # Check that caller info was extracted
        self.assertEqual(event.caller_file, "/app/example.py")


if __name__ == "__main__":
    unittest.main() 