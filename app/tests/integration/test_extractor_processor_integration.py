"""
Integration tests for the interaction between EventProcessor and extractors.

These tests verify that:
1. EventProcessor correctly finds applicable extractors for events
2. Extractors are properly registered and discovered
3. The event processing pipeline correctly applies multiple extractors to each event
4. Processed events are marked as processed
"""

import pytest
import json
from datetime import datetime
from unittest.mock import MagicMock, patch
import os
from sqlalchemy.ext.asyncio import AsyncSession

from app.business_logic.event_processor import EventProcessor
from app.business_logic.extractors.base import BaseExtractor, extractor_registry
from app.business_logic.extractors.llm_call_extractor import LLMCallExtractor
from app.business_logic.extractors.framework_extractor import FrameworkExtractor
from app.business_logic.extractors.monitor_event_extractor import MonitorEventExtractor
from app.models.event import Event
from app.models.model_details import ModelDetails
from app.models.token_usage import TokenUsage
from app.models.performance_metric import PerformanceMetric
from app.models.security_alert import SecurityAlert
from app.models.session import Session


class TestExtractorProcessorIntegration:
    """Tests for the integration between EventProcessor and various extractors."""
    
    @pytest.fixture
    def create_event(self):
        """Fixture to create test events based on type."""
        def _create_event(event_type, data, agent_id="test-agent", id_suffix=""):
            """Create a test event with the given properties."""
            event = MagicMock()
            event.id = f"test-event-{event_type}-{id_suffix}"
            event.event_type = event_type
            event.timestamp = datetime.now()
            event.agent_id = agent_id
            event.duration_ms = None
            event.is_processed = False
            event.data = data
            return event
        
        return _create_event
    
    @pytest.fixture
    def processor_with_custom_extractors(self):
        """Create an event processor with specific extractors for testing."""
        def _create_processor(extractors=None):
            """Create a processor with the given extractors or default ones."""
            if extractors is None:
                extractors = [
                    LLMCallExtractor(),
                    FrameworkExtractor(),
                    MonitorEventExtractor()
                ]
            return EventProcessor(extractors=extractors)
        
        return _create_processor
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session for testing."""
        session = MagicMock(spec=AsyncSession)
        
        # Set up mock methods for the session
        session.add = MagicMock()
        session.add_all = MagicMock()
        session.commit = MagicMock()
        session.rollback = MagicMock()
        session.execute = MagicMock()
        session.refresh = MagicMock()
        
        # Make commit and rollback async-compatible
        session.commit.return_value = None
        session.commit.__await__ = lambda self: (yield from [])
        
        session.rollback.return_value = None
        session.rollback.__await__ = lambda self: (yield from [])
        
        session.refresh.return_value = None
        session.refresh.__await__ = lambda self: (yield from [])
        
        return session
    
    @pytest.mark.asyncio
    async def test_processor_finds_applicable_extractors(self, create_event, processor_with_custom_extractors, mock_db_session):
        """Test that EventProcessor finds the right extractors for each event type."""
        # Create test events
        llm_event = create_event("LLM_call_start", {"method": "messages.create"}, id_suffix="1")
        framework_event = create_event("framework_patch", {"framework": {"name": "langchain"}}, id_suffix="2")
        monitor_event = create_event("monitor_init", {"timestamp": datetime.now().isoformat()}, id_suffix="3")
        unknown_event = create_event("unknown_type", {"data": "test"}, id_suffix="4")
        
        # Create processor with real extractors
        processor = processor_with_custom_extractors()
        
        # Test LLM event
        await processor.process_event(llm_event, mock_db_session)
        # LLM event should be processed by LLMCallExtractor
        assert llm_event.is_processed is True
        mock_db_session.add.assert_called()
        mock_db_session.commit.assert_called()
        
        # Reset mocks
        mock_db_session.reset_mock()
        
        # Test framework event
        await processor.process_event(framework_event, mock_db_session)
        # Framework event should be processed by FrameworkExtractor
        assert framework_event.is_processed is True
        mock_db_session.add.assert_called()
        mock_db_session.commit.assert_called()
        
        # Reset mocks
        mock_db_session.reset_mock()
        
        # Test monitor event
        await processor.process_event(monitor_event, mock_db_session)
        # Monitor event should be processed by MonitorEventExtractor
        assert monitor_event.is_processed is True
        mock_db_session.add.assert_called()
        mock_db_session.commit.assert_called()
        
        # Reset mocks
        mock_db_session.reset_mock()
        
        # Test unknown event
        await processor.process_event(unknown_event, mock_db_session)
        # Unknown event should still be marked as processed even though no extractors apply
        assert unknown_event.is_processed is True
        mock_db_session.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_process_events_batch(self, create_event, processor_with_custom_extractors, mock_db_session):
        """Test processing multiple events in a batch."""
        # Create test events
        events = [
            create_event("LLM_call_start", {"method": "messages.create"}, id_suffix="1"),
            create_event("framework_patch", {"framework": {"name": "langchain"}}, id_suffix="2"),
            create_event("monitor_init", {"timestamp": datetime.now().isoformat()}, id_suffix="3"),
            create_event("unknown_type", {"data": "test"}, id_suffix="4")
        ]
        
        # Create processor with real extractors
        processor = processor_with_custom_extractors()
        
        # Process events in batch
        processed_events = await processor.process_events(events, mock_db_session)
        
        # Verify all events were processed
        assert len(processed_events) == len(events)
        for event in processed_events:
            assert event.is_processed is True
        
        # Verify db session was used
        assert mock_db_session.commit.call_count >= len(events)
    
    @pytest.mark.asyncio
    async def test_extractor_error_handling(self, create_event, mock_db_session):
        """Test that errors in one extractor don't affect other extractors."""
        # Create a failing extractor
        failing_extractor = MagicMock(spec=BaseExtractor)
        failing_extractor.get_name.return_value = "FailingExtractor"
        failing_extractor.can_process.return_value = True
        failing_extractor.process.side_effect = Exception("Simulated extractor failure")
        
        # Create a working extractor
        working_extractor = MagicMock(spec=BaseExtractor)
        working_extractor.get_name.return_value = "WorkingExtractor"
        working_extractor.can_process.return_value = True
        
        # Make process async-compatible
        async def mock_process(event, db):
            event.processed_by_working = True
            return None
            
        working_extractor.process = mock_process
        
        # Create processor with our test extractors
        processor = EventProcessor(extractors=[failing_extractor, working_extractor])
        
        # Create test event
        test_event = create_event("test_event", {"data": "test"}, id_suffix="5")
        
        # Process the event
        await processor.process_event(test_event, mock_db_session)
        
        # Verify the event was still processed by the working extractor
        assert hasattr(test_event, 'processed_by_working')
        assert test_event.processed_by_working is True
        
        # Verify the event is marked as processed
        assert test_event.is_processed is True
        
        # Verify db session was committed
        mock_db_session.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_multiple_applicable_extractors(self, create_event, mock_db_session):
        """Test that multiple applicable extractors are all applied to the same event."""
        # Create multiple extractors that can all process the same event
        extractor1 = MagicMock(spec=BaseExtractor)
        extractor1.get_name.return_value = "Extractor1"
        extractor1.can_process.return_value = True
        
        extractor2 = MagicMock(spec=BaseExtractor)
        extractor2.get_name.return_value = "Extractor2"
        extractor2.can_process.return_value = True
        
        extractor3 = MagicMock(spec=BaseExtractor)
        extractor3.get_name.return_value = "Extractor3"
        extractor3.can_process.return_value = True
        
        # Make process functions async-compatible
        async def mock_process1(event, db):
            event.processed_by_1 = True
            return None
            
        async def mock_process2(event, db):
            event.processed_by_2 = True
            return None
            
        async def mock_process3(event, db):
            event.processed_by_3 = True
            return None
            
        extractor1.process = mock_process1
        extractor2.process = mock_process2
        extractor3.process = mock_process3
        
        # Create processor with our test extractors
        processor = EventProcessor(extractors=[extractor1, extractor2, extractor3])
        
        # Create test event
        test_event = create_event("test_event", {"data": "test"}, id_suffix="6")
        
        # Process the event
        await processor.process_event(test_event, mock_db_session)
        
        # Verify all extractors were applied
        assert test_event.processed_by_1 is True
        assert test_event.processed_by_2 is True
        assert test_event.processed_by_3 is True
        
        # Verify the event is marked as processed
        assert test_event.is_processed is True 