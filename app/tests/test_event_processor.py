"""
Tests for the EventProcessor.

This module contains tests for the EventProcessor that coordinates
processing events through the business logic layer.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

from app.business_logic.event_processor import EventProcessor
from app.business_logic.extractors.base import BaseExtractor


class MockExtractor(BaseExtractor):
    """Mock extractor for testing."""
    
    def __init__(self, can_process_result=True):
        self.can_process_result = can_process_result
        self.processed_events = []
    
    def can_process(self, event):
        return self.can_process_result
    
    async def process(self, event, db_session):
        self.processed_events.append(event)


class TestEventProcessor:
    """Tests for the EventProcessor."""
    
    @pytest.mark.asyncio
    async def test_process_event(self):
        """Test processing a single event."""
        # Create mock event and DB session
        event = MagicMock()
        event.id = 1
        event.event_type = "test_event"
        db_session = AsyncMock()
        
        # Create mock extractors
        extractor1 = MockExtractor(can_process_result=True)
        extractor2 = MockExtractor(can_process_result=False)
        extractor3 = MockExtractor(can_process_result=True)
        
        # Create processor with mock extractors
        processor = EventProcessor(extractors=[extractor1, extractor2, extractor3])
        
        # Process the event
        await processor.process_event(event, db_session)
        
        # Verify extractors were called correctly
        assert event in extractor1.processed_events
        assert event not in extractor2.processed_events
        assert event in extractor3.processed_events
        
        # Verify event was marked as processed
        assert event.is_processed is True
        
        # Verify session was committed
        db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_events(self):
        """Test processing multiple events."""
        # Create mock events and DB session
        event1 = MagicMock()
        event1.id = 1
        event1.event_type = "test_event_1"
        
        event2 = MagicMock()
        event2.id = 2
        event2.event_type = "test_event_2"
        
        db_session = AsyncMock()
        
        # Create mock extractor
        extractor = MockExtractor(can_process_result=True)
        
        # Create processor with mock extractor
        processor = EventProcessor(extractors=[extractor])
        
        # Process the events
        result = await processor.process_events([event1, event2], db_session)
        
        # Verify both events were processed
        assert len(result) == 2
        assert event1 in result
        assert event2 in result
        
        # Verify extractor was called for both events
        assert event1 in extractor.processed_events
        assert event2 in extractor.processed_events
        
        # Verify both events were marked as processed
        assert event1.is_processed is True
        assert event2.is_processed is True
        
        # Verify session was committed twice (once per event)
        assert db_session.commit.call_count == 2
    
    @pytest.mark.asyncio
    async def test_process_event_with_exception(self):
        """Test processing an event that raises an exception."""
        # Create mock event and DB session
        event = MagicMock()
        event.id = 1
        event.event_type = "test_event"
        db_session = AsyncMock()
        
        # Create mock extractor that raises an exception on the event processing step
        mock_extractor = AsyncMock(spec=BaseExtractor)
        mock_extractor.can_process.return_value = True
        mock_extractor.process.side_effect = Exception("Test exception")
        mock_extractor.get_name.return_value = "MockExtractor"
        
        # Create processor with mock extractor
        processor = EventProcessor(extractors=[mock_extractor])
        
        # Process the event - should log the error but continue execution
        await processor.process_event(event, db_session)
        
        # Verify extractor was called
        mock_extractor.process.assert_called_once()
        
        # Verify event was still marked as processed
        assert event.is_processed is True
        
        # Verify session was still committed
        db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_extractors_for_event_type():
    """Test getting extractors for a specific event type."""
    # Create mock registry with mock extractors
    mock_registry = MagicMock()
    mock_registry.get_extractors_for_event.return_value = ["extractor1", "extractor2"]
    
    # Patch the extractor_registry
    with patch("app.business_logic.event_processor.extractor_registry", mock_registry):
        # Get extractors for event type
        result = await EventProcessor.get_extractors_for_event_type("test_event")
        
        # Verify registry was called correctly
        mock_registry.get_extractors_for_event.assert_called_once()
        
        # Verify the mock event had the correct event_type
        args, _ = mock_registry.get_extractors_for_event.call_args
        mock_event = args[0]
        assert mock_event.event_type == "test_event"
        
        # Verify correct extractors were returned
        assert result == ["extractor1", "extractor2"] 