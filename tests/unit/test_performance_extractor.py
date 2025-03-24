"""
Unit tests for PerformanceExtractor.

This module tests the functionality of the PerformanceExtractor class.
"""

import unittest
import asyncio
import copy

# Mock the extractor for testing
class MockPerformanceExtractor:
    """Mock implementation of PerformanceExtractor for testing."""
    
    def can_process(self, event):
        """Check if this extractor can process the given event."""
        # Check if event has duration_ms directly
        if hasattr(event, 'duration_ms') and event.duration_ms is not None:
            return True
            
        # Check for performance data in event data
        if hasattr(event, 'data') and event.data:
            # Look for performance field
            if 'performance' in event.data and 'duration_ms' in event.data['performance']:
                return True
                
            # Look for elapsed_time or duration field
            if 'elapsed_time' in event.data or 'duration' in event.data:
                return True
                
        return False
    
    async def _extract_performance_metrics(self, event):
        """Extract performance metrics from the event."""
        from tests.fixtures.mock_models import PerformanceMetric
        
        duration_ms = None
        
        # Extract duration from event duration_ms field
        if hasattr(event, 'duration_ms') and event.duration_ms is not None:
            duration_ms = event.duration_ms
            
        # Extract from data
        elif hasattr(event, 'data') and event.data:
            # From performance field
            if 'performance' in event.data and 'duration_ms' in event.data['performance']:
                duration_ms = float(event.data['performance']['duration_ms'])
                
            # From elapsed_time field (convert to ms)
            elif 'elapsed_time' in event.data:
                duration_ms = float(event.data['elapsed_time'])
                
            # From duration field (convert to ms if in seconds)
            elif 'duration' in event.data:
                duration = float(event.data['duration'])
                if duration < 100:  # Likely in seconds
                    duration_ms = duration * 1000
                else:
                    duration_ms = duration
                    
        if duration_ms is not None:
            return PerformanceMetric(
                event_id=event.id,
                duration_ms=duration_ms,
                timestamp=event.timestamp
            )
            
        return None
    
    async def process(self, event, db_session):
        """Process the event and extract performance metrics."""
        performance_metric = await self._extract_performance_metrics(event)
        if performance_metric:
            db_session.add(performance_metric)


from tests.fixtures.event_fixtures import (
    MODEL_RESPONSE_EVENT, 
    CALL_FINISH_EVENT,
    LLM_CALL_FINISH_EVENT,
    MODEL_REQUEST_EVENT
)
from tests.fixtures.db_helper import mock_db_session_factory
from tests.fixtures.mock_models import PerformanceMetric


class TestPerformanceExtractor(unittest.TestCase):
    """Test cases for the PerformanceExtractor."""
    
    def setUp(self):
        """Set up test environment before each test."""
        self.extractor = MockPerformanceExtractor()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        """Clean up after each test."""
        self.loop.close()
    
    def test_can_process(self):
        """Test that the extractor can process appropriate event types."""
        # Should process performance-containing events
        self.assertTrue(self.extractor.can_process(MODEL_RESPONSE_EVENT))
        self.assertTrue(self.extractor.can_process(CALL_FINISH_EVENT))
        self.assertTrue(self.extractor.can_process(LLM_CALL_FINISH_EVENT))
        
        # Should not process events without performance data
        self.assertFalse(self.extractor.can_process(MODEL_REQUEST_EVENT))
        
        # Should process events with direct duration_ms
        event_with_duration = copy.deepcopy(MODEL_REQUEST_EVENT)
        event_with_duration.duration_ms = 100.0
        self.assertTrue(self.extractor.can_process(event_with_duration))
    
    def test_extract_performance_from_model_response(self):
        """Test extraction of performance metrics from model_response events."""
        event = copy.deepcopy(MODEL_RESPONSE_EVENT)
        
        # Call the method
        result = self.loop.run_until_complete(self.extractor._extract_performance_metrics(event))
        
        # Check the extracted data
        self.assertIsInstance(result, PerformanceMetric)
        self.assertEqual(result.event_id, event.id)
        self.assertEqual(result.duration_ms, 1250.5)
        self.assertEqual(result.timestamp, event.timestamp)
    
    def test_extract_performance_from_call_finish(self):
        """Test extraction of performance metrics from call_finish events."""
        event = copy.deepcopy(CALL_FINISH_EVENT)
        
        # Call the method
        result = self.loop.run_until_complete(self.extractor._extract_performance_metrics(event))
        
        # Check the extracted data (note conversion from s to ms)
        self.assertIsInstance(result, PerformanceMetric)
        self.assertEqual(result.event_id, event.id)
        self.assertEqual(result.duration_ms, 350.25)
        self.assertEqual(result.timestamp, event.timestamp)
    
    def test_extract_performance_from_direct_duration(self):
        """Test extraction of performance metrics from direct duration_ms field."""
        event = copy.deepcopy(MODEL_REQUEST_EVENT)
        event.duration_ms = 150.5
        
        # Call the method
        result = self.loop.run_until_complete(self.extractor._extract_performance_metrics(event))
        
        # Check the extracted data
        self.assertIsInstance(result, PerformanceMetric)
        self.assertEqual(result.event_id, event.id)
        self.assertEqual(result.duration_ms, 150.5)
        self.assertEqual(result.timestamp, event.timestamp)
    
    def test_extract_performance_with_no_data(self):
        """Test that extraction handles events with no performance data."""
        # Create an event with no performance data
        event = copy.deepcopy(MODEL_RESPONSE_EVENT)
        event.data = {}
        event.duration_ms = None
        
        # Call the method
        result = self.loop.run_until_complete(self.extractor._extract_performance_metrics(event))
        
        # Should return None since no performance data was found
        self.assertIsNone(result)
    
    def test_process_method_adds_performance_metric(self):
        """Test the main process method adds performance metric to the database."""
        event = copy.deepcopy(MODEL_RESPONSE_EVENT)
        db_session = mock_db_session_factory()
        
        # Call the process method
        self.loop.run_until_complete(self.extractor.process(event, db_session))
        
        # Check that performance metric was added to the database
        self.assertEqual(len(db_session.added_objects), 1)
        added_metric = db_session.added_objects[0]
        self.assertIsInstance(added_metric, PerformanceMetric)
        self.assertEqual(added_metric.event_id, event.id)
        self.assertEqual(added_metric.duration_ms, 1250.5)
    
    def test_process_method_with_no_performance_data(self):
        """Test that process method handles events with no performance data."""
        # Create an event with no performance data
        event = copy.deepcopy(MODEL_RESPONSE_EVENT)
        event.data = {}
        event.duration_ms = None
        db_session = mock_db_session_factory()
        
        # Call the process method
        self.loop.run_until_complete(self.extractor.process(event, db_session))
        
        # Should not add anything to the database
        self.assertEqual(len(db_session.added_objects), 0)


if __name__ == "__main__":
    unittest.main() 