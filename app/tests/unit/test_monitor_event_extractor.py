"""
Unit test for MonitorEventExtractor.

Tests the extraction of data from monitor_init and monitor_shutdown events.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch

from app.business_logic.extractors.monitor_event_extractor import MonitorEventExtractor
from app.models.session import Session


class TestMonitorEventExtractor:
    """Tests for the MonitorEventExtractor."""
    
    @pytest.fixture
    def extractor(self):
        """Create a MonitorEventExtractor instance for testing."""
        return MonitorEventExtractor()
    
    @pytest.fixture
    def mock_event_init(self):
        """Create a mock monitor_init event for testing."""
        event = MagicMock()
        event.id = "test-event-id-1"
        event.event_type = "monitor_init"
        event.timestamp = datetime.now()
        event.agent_id = "test-agent"
        event.data = {
            "timestamp": datetime.now().isoformat(),
            "api_endpoint": "https://api.example.com",
            "log_file": "output/test_monitoring.json",
            "llm_provider": "OpenAI",
            "debug_level": "INFO",
            "development_mode": True
        }
        return event
    
    @pytest.fixture
    def mock_event_shutdown(self):
        """Create a mock monitor_shutdown event for testing."""
        event = MagicMock()
        event.id = "test-event-id-2"
        event.event_type = "monitor_shutdown"
        event.timestamp = datetime.now()
        event.agent_id = "test-agent"
        event.data = {
            "timestamp": datetime.now().isoformat()
        }
        return event
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        session.add = AsyncMock()
        session.query = MagicMock()
        
        # Set up mock for session query
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_order_by = MagicMock()
        mock_first = AsyncMock()
        
        session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order_by
        mock_order_by.first.return_value = mock_first
        
        # Create a mock session object to be returned by the query
        mock_session = Session(
            agent_id="test-agent",
            start_time=datetime.now(),
            active=True,
            configuration={}
        )
        
        mock_first.return_value = mock_session
        
        return session
    
    def test_can_process(self, extractor, mock_event_init, mock_event_shutdown):
        """Test that the extractor can identify monitor events."""
        # Should process monitor_init events
        assert extractor.can_process(mock_event_init) is True
        
        # Should process monitor_shutdown events
        assert extractor.can_process(mock_event_shutdown) is True
        
        # Should not process other event types
        other_event = MagicMock()
        other_event.event_type = "some_other_event"
        assert extractor.can_process(other_event) is False
    
    @pytest.mark.asyncio
    async def test_process_monitor_init(self, extractor, mock_event_init, mock_db_session):
        """Test processing a monitor_init event."""
        # Process the event
        await extractor._process_monitor_init(mock_event_init, mock_db_session)
        
        # Verify that a session was added to the database
        assert mock_db_session.add.called
        
        # Get the session that was added
        call_args = mock_db_session.add.call_args
        session = call_args[0][0]
        
        # Verify the session fields
        assert isinstance(session, Session)
        assert session.agent_id == mock_event_init.agent_id
        assert session.start_time == mock_event_init.timestamp
        assert session.active is True
        assert session.end_time is None
        
        # Verify configuration details
        assert session.configuration["api_endpoint"] == "https://api.example.com"
        assert session.configuration["log_file"] == "output/test_monitoring.json"
        assert session.configuration["llm_provider"] == "OpenAI"
        assert session.configuration["debug_level"] == "INFO"
        assert session.configuration["development_mode"] is True
    
    @pytest.mark.asyncio
    async def test_process_monitor_shutdown(self, extractor, mock_event_shutdown, mock_db_session):
        """Test processing a monitor_shutdown event."""
        # Process the event
        await extractor._process_monitor_shutdown(mock_event_shutdown, mock_db_session)
        
        # Verify that session.query was called to find the active session
        assert mock_db_session.query.called
        
        # Verify that the session was updated
        assert mock_db_session.add.called
        
        # Get the active session from the mock setup
        mock_query_result = mock_db_session.query().filter().order_by().first()
        
        # Check that the session was marked as inactive and end time was set
        assert mock_query_result.active is False
        assert mock_query_result.end_time == mock_event_shutdown.timestamp
    
    @pytest.mark.asyncio
    async def test_process(self, extractor, mock_event_init, mock_event_shutdown, mock_db_session):
        """Test the main process method with different event types."""
        # Patch the specialized processing methods
        with patch.object(extractor, '_process_monitor_init', new=AsyncMock()) as mock_init:
            with patch.object(extractor, '_process_monitor_shutdown', new=AsyncMock()) as mock_shutdown:
                
                # Test processing init event
                await extractor.process(mock_event_init, mock_db_session)
                assert mock_init.called
                assert not mock_shutdown.called
                
                # Reset mocks
                mock_init.reset_mock()
                mock_shutdown.reset_mock()
                
                # Test processing shutdown event
                await extractor.process(mock_event_shutdown, mock_db_session)
                assert not mock_init.called
                assert mock_shutdown.called
    
    @pytest.mark.asyncio
    async def test_process_with_no_data(self, extractor, mock_db_session):
        """Test processing an event with no data."""
        # Create an event with no data
        event = MagicMock()
        event.event_type = "monitor_init"
        event.data = None
        
        # Process the event
        await extractor.process(event, mock_db_session)
        
        # Verify that no session was added to the database
        assert not mock_db_session.add.called 