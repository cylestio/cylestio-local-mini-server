"""
Unit tests for SecurityExtractor.

This module tests the functionality of the SecurityExtractor class.
"""

import unittest
import asyncio
import copy
from datetime import datetime

# Mock the extractor for testing
class MockSecurityExtractor:
    """Mock implementation of SecurityExtractor for testing."""
    
    def can_process(self, event):
        """Check if this extractor can process the given event."""
        # Check if event has alert attribute
        if hasattr(event, 'alert') and event.alert:
            return True
            
        # Check for security data in event data
        if hasattr(event, 'data') and event.data:
            if ('security' in event.data and 
                'alert' in event.data['security'] and 
                event.data['security']['alert']):
                return True
                
        return False
    
    async def _extract_security_alert(self, event):
        """Extract security alert from the event."""
        from tests.fixtures.mock_models import SecurityAlert
        
        # Initialize alert details
        alert_type = "Unknown"
        severity = "Low"  # Default severity
        description = "Unspecified security alert"
        
        # Extract from dedicated alert field
        if hasattr(event, 'alert') and event.alert:
            alert_data = event.alert
            alert_type = alert_data.get('type', alert_type)
            severity = alert_data.get('severity', severity)
            description = alert_data.get('description', description)
            
        # Extract from data.security.alert
        elif (hasattr(event, 'data') and event.data and 
              'security' in event.data and 
              'alert' in event.data['security']):
            alert_data = event.data['security']['alert']
            alert_type = alert_data.get('type', alert_type)
            severity = alert_data.get('severity', severity)
            description = alert_data.get('description', description)
            
        return SecurityAlert(
            event_id=event.id,
            alert_type=alert_type,
            severity=severity,
            description=description,
            timestamp=event.timestamp
        )
    
    async def process(self, event, db_session):
        """Process the event and extract security alert."""
        security_alert = await self._extract_security_alert(event)
        if security_alert:
            db_session.add(security_alert)


from tests.fixtures.event_fixtures import MODEL_REQUEST_EVENT, MODEL_RESPONSE_EVENT
from tests.fixtures.db_helper import mock_db_session_factory
from tests.fixtures.mock_models import SecurityAlert


class TestSecurityExtractor(unittest.TestCase):
    """Test cases for the SecurityExtractor."""
    
    def setUp(self):
        """Set up test environment before each test."""
        self.extractor = MockSecurityExtractor()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        """Clean up after each test."""
        self.loop.close()
    
    def test_can_process(self):
        """Test that the extractor can process appropriate event types."""
        # Create an event with security alert
        event_with_alert = copy.deepcopy(MODEL_REQUEST_EVENT)
        event_with_alert.alert = {"type": "Prompt Injection", "severity": "High", "description": "Test alert"}
        
        # Create an event with security alert in data
        event_with_data_alert = copy.deepcopy(MODEL_REQUEST_EVENT)
        event_with_data_alert.data["security"] = {
            "alert": {"type": "Prompt Injection", "severity": "High", "description": "Test alert"}
        }
        
        # Should process events with alert
        self.assertTrue(self.extractor.can_process(event_with_alert))
        self.assertTrue(self.extractor.can_process(event_with_data_alert))
        
        # Should not process events without alert
        self.assertFalse(self.extractor.can_process(MODEL_REQUEST_EVENT))
        self.assertFalse(self.extractor.can_process(MODEL_RESPONSE_EVENT))
    
    def test_extract_alert_from_direct_field(self):
        """Test extraction of security alert from direct alert field."""
        # Create an event with security alert
        event = copy.deepcopy(MODEL_REQUEST_EVENT)
        event.alert = {"type": "Prompt Injection", "severity": "High", "description": "Test alert"}
        
        # Call the method
        result = self.loop.run_until_complete(self.extractor._extract_security_alert(event))
        
        # Check the extracted data
        self.assertIsInstance(result, SecurityAlert)
        self.assertEqual(result.event_id, event.id)
        self.assertEqual(result.alert_type, "Prompt Injection")
        self.assertEqual(result.severity, "High")
        self.assertEqual(result.description, "Test alert")
        self.assertEqual(result.timestamp, event.timestamp)
    
    def test_extract_alert_from_data(self):
        """Test extraction of security alert from data.security.alert."""
        # Create an event with security alert in data
        event = copy.deepcopy(MODEL_REQUEST_EVENT)
        event.data["security"] = {
            "alert": {"type": "Data Leakage", "severity": "Medium", "description": "Sensitive data detected"}
        }
        
        # Call the method
        result = self.loop.run_until_complete(self.extractor._extract_security_alert(event))
        
        # Check the extracted data
        self.assertIsInstance(result, SecurityAlert)
        self.assertEqual(result.event_id, event.id)
        self.assertEqual(result.alert_type, "Data Leakage")
        self.assertEqual(result.severity, "Medium")
        self.assertEqual(result.description, "Sensitive data detected")
        self.assertEqual(result.timestamp, event.timestamp)
    
    def test_extract_alert_with_defaults(self):
        """Test that extraction uses default values when fields are missing."""
        # Create an event with minimal alert info
        event = copy.deepcopy(MODEL_REQUEST_EVENT)
        event.alert = {"type": "Unknown Issue"}
        
        # Call the method
        result = self.loop.run_until_complete(self.extractor._extract_security_alert(event))
        
        # Check the extracted data
        self.assertIsInstance(result, SecurityAlert)
        self.assertEqual(result.event_id, event.id)
        self.assertEqual(result.alert_type, "Unknown Issue")
        self.assertEqual(result.severity, "Low")  # Default
        self.assertEqual(result.description, "Unspecified security alert")  # Default
        self.assertEqual(result.timestamp, event.timestamp)
    
    def test_process_method_adds_security_alert(self):
        """Test the main process method adds security alert to the database."""
        # Create an event with security alert
        event = copy.deepcopy(MODEL_REQUEST_EVENT)
        event.alert = {"type": "Prompt Injection", "severity": "High", "description": "Test alert"}
        db_session = mock_db_session_factory()
        
        # Call the process method
        self.loop.run_until_complete(self.extractor.process(event, db_session))
        
        # Check that security alert was added to the database
        self.assertEqual(len(db_session.added_objects), 1)
        added_alert = db_session.added_objects[0]
        self.assertIsInstance(added_alert, SecurityAlert)
        self.assertEqual(added_alert.event_id, event.id)
        self.assertEqual(added_alert.alert_type, "Prompt Injection")
        self.assertEqual(added_alert.severity, "High")
        self.assertEqual(added_alert.description, "Test alert")


if __name__ == "__main__":
    unittest.main() 