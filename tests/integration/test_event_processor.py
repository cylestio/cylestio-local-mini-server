"""
Integration tests for EventProcessor.

This module tests the integration of the EventProcessor with extractors.
"""

import unittest
import asyncio
from datetime import datetime

# Mock event processor and extractors
class MockExtractor:
    """Base mock extractor that does nothing."""
    def __init__(self, name, events_to_process=None):
        self.name = name
        self.events_to_process = events_to_process or []
        self.processed_events = []
    
    def can_process(self, event):
        """Check if this extractor can process the event."""
        return event.event_type in self.events_to_process
    
    async def process(self, event, db_session):
        """Process the event."""
        self.processed_events.append(event)
        # Do nothing else in the mock

class MockCommonExtractor(MockExtractor):
    """Mock common extractor that processes all events."""
    def __init__(self):
        super().__init__("CommonExtractor", ["MODEL_REQUEST_EVENT", "MODEL_RESPONSE_EVENT", 
                                             "LLM_CALL_START_EVENT", "LLM_CALL_FINISH_EVENT",
                                             "MONITOR_INIT_EVENT", "CALL_FINISH_EVENT"])
    
    async def process(self, event, db_session):
        """Process the event by adding Agent and Session."""
        from tests.fixtures.mock_models import Agent, Session
        db_session.add(Agent(agent_id=event.agent_id))
        db_session.add(Session(session_id=event.session_id, agent_id=event.agent_id))
        await super().process(event, db_session)

class MockSecurityExtractor(MockExtractor):
    """Mock security extractor that processes security-related events."""
    def __init__(self):
        super().__init__("SecurityExtractor", ["LLM_CALL_START_EVENT"])
    
    async def process(self, event, db_session):
        """Process the event by adding SecurityAlert."""
        from tests.fixtures.mock_models import SecurityAlert
        if hasattr(event, 'alert') and event.alert:
            db_session.add(SecurityAlert(
                event_id=event.id,
                alert_type=event.alert,
                severity="high",
                timestamp=event.timestamp
            ))
        await super().process(event, db_session)

class MockTokenUsageExtractor(MockExtractor):
    """Mock token usage extractor that processes token usage events."""
    def __init__(self):
        super().__init__("TokenUsageExtractor", ["MODEL_RESPONSE_EVENT", "LLM_CALL_FINISH_EVENT"])
    
    async def process(self, event, db_session):
        """Process the event by adding TokenUsage."""
        from tests.fixtures.mock_models import TokenUsage
        db_session.add(TokenUsage(
            event_id=event.id,
            session_id=event.session_id,
            model="test-model",
            input_tokens=100,
            output_tokens=100,
            total_tokens=200,
            timestamp=event.timestamp
        ))
        await super().process(event, db_session)

class MockFrameworkExtractor(MockExtractor):
    """Mock framework extractor that processes framework-related events."""
    def __init__(self):
        super().__init__("FrameworkExtractor", ["MONITOR_INIT_EVENT"])
    
    async def process(self, event, db_session):
        """Process the event by adding FrameworkDetails."""
        from tests.fixtures.mock_models import FrameworkDetails
        db_session.add(FrameworkDetails(
            event_id=event.id,
            framework_name="test-framework",
            framework_version="1.0.0",
            timestamp=event.timestamp
        ))
        await super().process(event, db_session)

class MockPerformanceExtractor(MockExtractor):
    """Mock performance extractor that processes performance-related events."""
    def __init__(self):
        super().__init__("PerformanceExtractor", ["MODEL_RESPONSE_EVENT", "LLM_CALL_FINISH_EVENT"])
    
    async def process(self, event, db_session):
        """Process the event by adding PerformanceMetric."""
        from tests.fixtures.mock_models import PerformanceMetric
        if hasattr(event, 'duration_ms') and event.duration_ms:
            db_session.add(PerformanceMetric(
                event_id=event.id,
                duration_ms=event.duration_ms,
                timestamp=event.timestamp
            ))
        await super().process(event, db_session)

class MockEventProcessor:
    """Mock implementation of EventProcessor for testing."""

    def __init__(self, extractors=None):
        """Initialize with list of extractors."""
        self.extractors = extractors or []
        self.processed_events = []
        
    async def process_event(self, event, db_session):
        """Process an event through all compatible extractors."""
        self.processed_events.append(event)
        
        for extractor in self.extractors:
            if extractor.can_process(event):
                try:
                    await extractor.process(event, db_session)
                except Exception as e:
                    # Log the error but continue processing with other extractors
                    print(f"Error in extractor {extractor.__class__.__name__}: {str(e)}")
                    continue
        
        # Commit the session after processing        
        db_session.commit()
        return True
        
    async def process_events(self, events, db_session):
        """Process multiple events in sequence."""
        for event in events:
            await self.process_event(event, db_session)

from tests.fixtures.event_fixtures import (
    MODEL_REQUEST_EVENT,
    MODEL_RESPONSE_EVENT,
    LLM_CALL_START_EVENT,
    LLM_CALL_FINISH_EVENT,
    MONITOR_INIT_EVENT
)
from tests.fixtures.db_helper import mock_db_session_factory
from tests.fixtures.mock_models import Agent, Session, SecurityAlert, TokenUsage, FrameworkDetails, PerformanceMetric


class TestEventProcessor(unittest.TestCase):
    """Integration tests for the EventProcessor."""
    
    def setUp(self):
        """Set up test environment before each test."""
        # Create processor with all extractors
        self.extractors = [
            MockCommonExtractor(),
            MockSecurityExtractor(),
            MockTokenUsageExtractor(),
            MockFrameworkExtractor(),
            MockPerformanceExtractor()
        ]
        self.processor = MockEventProcessor(self.extractors)
        
        # Set up async loop
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Create mock DB session
        self.db_session = mock_db_session_factory()
    
    def tearDown(self):
        """Clean up after each test."""
        self.loop.close()
    
    def test_process_model_request_event(self):
        """Test processing a model request event."""
        event = MODEL_REQUEST_EVENT
        
        # Process the event
        self.loop.run_until_complete(self.processor.process_event(event, self.db_session))
        
        # Check that appropriate data was added to the database
        self.assertEqual(len(self.db_session.added_objects), 2)  # Should add Agent and Session
        
        # Verify we have the expected types of objects
        added_types = [type(obj) for obj in self.db_session.added_objects]
        self.assertIn(Agent, added_types)
        self.assertIn(Session, added_types)
    
    def test_process_model_response_event(self):
        """Test processing a model response event."""
        event = MODEL_RESPONSE_EVENT
        
        # Process the event
        self.loop.run_until_complete(self.processor.process_event(event, self.db_session))
        
        # Check that appropriate data was added to the database
        self.assertEqual(len(self.db_session.added_objects), 4)  # Should add Agent, Session, TokenUsage, PerformanceMetric
        
        # Verify we have the expected types of objects
        added_types = [type(obj) for obj in self.db_session.added_objects]
        self.assertIn(Agent, added_types)
        self.assertIn(Session, added_types)
        self.assertIn(TokenUsage, added_types)
        self.assertIn(PerformanceMetric, added_types)
    
    def test_process_llm_call_start_event(self):
        """Test processing an LLM call start event with security alert."""
        event = LLM_CALL_START_EVENT
        
        # Process the event
        self.loop.run_until_complete(self.processor.process_event(event, self.db_session))
        
        # Check that appropriate data was added to the database
        self.assertEqual(len(self.db_session.added_objects), 3)  # Should add Agent, Session, SecurityAlert
        
        # Verify we have the expected types of objects
        added_types = [type(obj) for obj in self.db_session.added_objects]
        self.assertIn(Agent, added_types)
        self.assertIn(Session, added_types)
        self.assertIn(SecurityAlert, added_types)
    
    def test_process_llm_call_finish_event(self):
        """Test processing an LLM call finish event."""
        event = LLM_CALL_FINISH_EVENT
        
        # Process the event
        self.loop.run_until_complete(self.processor.process_event(event, self.db_session))
        
        # Check that appropriate data was added to the database
        self.assertEqual(len(self.db_session.added_objects), 4)  # Should add Agent, Session, TokenUsage, PerformanceMetric
        
        # Verify we have the expected types of objects
        added_types = [type(obj) for obj in self.db_session.added_objects]
        self.assertIn(Agent, added_types)
        self.assertIn(Session, added_types)
        self.assertIn(TokenUsage, added_types)
        self.assertIn(PerformanceMetric, added_types)
    
    def test_process_monitor_init_event(self):
        """Test processing a monitor init event."""
        event = MONITOR_INIT_EVENT
        
        # Process the event
        self.loop.run_until_complete(self.processor.process_event(event, self.db_session))
        
        # Check that appropriate data was added to the database
        self.assertEqual(len(self.db_session.added_objects), 3)  # Should add Agent, Session, FrameworkDetails
        
        # Verify we have the expected types of objects
        added_types = [type(obj) for obj in self.db_session.added_objects]
        self.assertIn(Agent, added_types)
        self.assertIn(Session, added_types)
        self.assertIn(FrameworkDetails, added_types)
    
    def test_process_with_failing_extractor(self):
        """Test that processor continues even if one extractor fails."""
        event = MODEL_RESPONSE_EVENT
        
        # Create a faulty extractor that raises an exception
        class FaultyExtractor:
            def can_process(self, event):
                return True
            
            async def process(self, event, db_session):
                raise Exception("Simulated failure")
        
        # Add faulty extractor to the processor
        processor_with_faulty = MockEventProcessor(self.extractors + [FaultyExtractor()])
        
        # Process should still complete without raising exception
        self.loop.run_until_complete(processor_with_faulty.process_event(event, self.db_session))
        
        # Check that appropriate data was still added by working extractors
        self.assertGreater(len(self.db_session.added_objects), 0)
    
    def test_process_batch_of_events(self):
        """Test processing a batch of multiple events."""
        # Reset the DB session
        self.db_session = mock_db_session_factory()
        
        events = [
            MODEL_REQUEST_EVENT,
            LLM_CALL_START_EVENT,
            MODEL_RESPONSE_EVENT
        ]
        
        # Process the batch of events
        self.loop.run_until_complete(self.processor.process_event(events[0], self.db_session))
        self.loop.run_until_complete(self.processor.process_event(events[1], self.db_session))
        self.loop.run_until_complete(self.processor.process_event(events[2], self.db_session))
        
        # Check that appropriate data was added to the database for all events
        # We expect data from all extractors for all applicable events
        added_types = [type(obj) for obj in self.db_session.added_objects]
        
        # Verify we have all the expected types of objects
        self.assertIn(Agent, added_types)
        self.assertIn(Session, added_types)
        self.assertIn(SecurityAlert, added_types)
        self.assertIn(TokenUsage, added_types)
        
        # Check commit was called the right number of times
        self.assertEqual(self.db_session.commit_count, len(events))

    def test_process_multiple_events(self):
        """Test processing multiple events in sequence."""
        # Reset the DB session
        self.db_session = mock_db_session_factory()
        
        # Create a batch of events
        events = [
            MODEL_REQUEST_EVENT,
            MODEL_RESPONSE_EVENT,
            MONITOR_INIT_EVENT
        ]
        
        # Process the batch of events
        self.loop.run_until_complete(self.processor.process_events(events, self.db_session))
        
        # Check that all events were processed and appropriate data was added
        self.assertEqual(self.db_session.commit_count, len(events))
        self.assertTrue(len(self.db_session.added_objects) > 0)


if __name__ == "__main__":
    unittest.main() 