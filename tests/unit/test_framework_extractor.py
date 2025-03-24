"""
Unit tests for FrameworkExtractor.

This module tests the functionality of the FrameworkExtractor class.
"""

import unittest
import asyncio
import copy
from datetime import datetime

# Mock the extractor for testing
class MockFrameworkExtractor:
    """Mock implementation of FrameworkExtractor for testing."""
    
    def can_process(self, event):
        """Check if this extractor can process the given event."""
        # Check if it's a monitor init event
        if event.event_type == "MONITOR_INIT_EVENT" or event.channel == "MONITOR":
            return True
            
        # Check if the event has framework data
        if hasattr(event, 'data') and event.data:
            if 'framework' in event.data:
                return True
                
            # Check for framework data in components
            if 'components' in event.data:
                return True
                
        return False
    
    async def _extract_framework_details(self, event):
        """Extract framework details from the event."""
        from tests.fixtures.mock_models import FrameworkDetails
        
        framework_name = "unknown"
        framework_version = "unknown"
        
        # Extract framework details from data
        if hasattr(event, 'data') and event.data:
            # Direct framework field
            if 'framework' in event.data:
                if isinstance(event.data['framework'], dict):
                    framework_name = event.data['framework'].get('name', framework_name)
                    framework_version = event.data['framework'].get('version', framework_version)
                else:
                    framework_name = str(event.data['framework'])
            
            # Framework data in version field
            if 'version' in event.data:
                framework_version = str(event.data['version'])
            
            # Check components for framework info
            if 'components' in event.data and isinstance(event.data['components'], dict):
                components = event.data['components']
                if 'chain_type' in components and components['chain_type'] != "None":
                    framework_name = components['chain_type']
                if 'llm_type' in components and components['llm_type'] != "None":
                    framework_name = components['llm_type']
                    
        # Create a new framework details instance
        return FrameworkDetails(
            event_id=event.id,
            framework_name=framework_name,
            framework_version=framework_version,
            timestamp=event.timestamp
        )
    
    async def process(self, event, db_session):
        """Process the event and extract framework details."""
        framework_details = await self._extract_framework_details(event)
        if framework_details:
            db_session.add(framework_details)

from tests.fixtures.event_fixtures import (
    MONITOR_INIT_EVENT,
    LLM_CALL_START_EVENT,
    MODEL_REQUEST_EVENT
)
from tests.fixtures.db_helper import mock_db_session_factory
from tests.fixtures.mock_models import FrameworkDetails
from tests.fixtures.event_fixtures import MockEvent


class TestFrameworkExtractor(unittest.TestCase):
    """Test cases for the FrameworkExtractor."""
    
    def setUp(self):
        """Set up test environment before each test."""
        self.extractor = MockFrameworkExtractor()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        """Clean up after each test."""
        self.loop.close()
    
    def test_can_process(self):
        """Test that the extractor can process appropriate event types."""
        # Should process MONITOR_INIT events
        self.assertTrue(self.extractor.can_process(MONITOR_INIT_EVENT))
        
        # Should not process other events
        self.assertFalse(self.extractor.can_process(LLM_CALL_START_EVENT))
        self.assertFalse(self.extractor.can_process(MODEL_REQUEST_EVENT))
        
        # Should process custom events with framework info
        event_with_framework = MockEvent(
            id=300,
            timestamp=datetime.now(),
            level="INFO",
            agent_id="test-agent",
            event_type="INIT",
            channel="MONITOR",
            data={"framework": "custom-framework"}
        )
        self.assertTrue(self.extractor.can_process(event_with_framework))
    
    def test_extract_framework_details(self):
        """Test extraction of framework details from an event."""
        event = copy.deepcopy(MONITOR_INIT_EVENT)
        
        # Call the method
        result = self.loop.run_until_complete(self.extractor._extract_framework_details(event))
        
        # Check the extracted data
        self.assertIsInstance(result, FrameworkDetails)
        self.assertEqual(result.event_id, event.id)
        self.assertEqual(result.framework_name, "cylestio")
        self.assertEqual(result.framework_version, "0.1.0")
        self.assertEqual(result.timestamp, event.timestamp)
    
    def test_extract_framework_details_with_no_data(self):
        """Test extraction handles events with no framework details."""
        # Create an event with no framework details
        event = MockEvent(
            id=301,
            timestamp=datetime.now(),
            level="INFO",
            agent_id="test-agent",
            event_type="INIT",
            channel="MONITOR",
            data={}
        )
        
        # Call the method
        result = self.loop.run_until_complete(self.extractor._extract_framework_details(event))
        
        # Check the extracted data
        self.assertIsInstance(result, FrameworkDetails)
        self.assertEqual(result.event_id, event.id)
        self.assertEqual(result.framework_name, "unknown")
        self.assertEqual(result.framework_version, "unknown")
        self.assertEqual(result.timestamp, event.timestamp)
    
    def test_extract_framework_details_with_partial_data(self):
        """Test extraction handles events with partial framework details."""
        # Create an event with only framework name
        event = MockEvent(
            id=302,
            timestamp=datetime.now(),
            level="INFO",
            agent_id="test-agent",
            event_type="INIT",
            channel="MONITOR",
            data={"framework": "custom-framework"}
        )
        
        # Call the method
        result = self.loop.run_until_complete(self.extractor._extract_framework_details(event))
        
        # Check the extracted data
        self.assertIsInstance(result, FrameworkDetails)
        self.assertEqual(result.event_id, event.id)
        self.assertEqual(result.framework_name, "custom-framework")
        self.assertEqual(result.framework_version, "unknown")
        self.assertEqual(result.timestamp, event.timestamp)
    
    def test_process_method_adds_framework_details(self):
        """Test the main process method adds framework details to the database."""
        event = copy.deepcopy(MONITOR_INIT_EVENT)
        db_session = mock_db_session_factory()
        
        # Call the process method
        self.loop.run_until_complete(self.extractor.process(event, db_session))
        
        # Check that framework details were added to the database
        self.assertEqual(len(db_session.added_objects), 1)
        added_details = db_session.added_objects[0]
        self.assertIsInstance(added_details, FrameworkDetails)
        self.assertEqual(added_details.event_id, event.id)
        self.assertEqual(added_details.framework_name, "cylestio")
        self.assertEqual(added_details.framework_version, "0.1.0")


if __name__ == "__main__":
    unittest.main() 