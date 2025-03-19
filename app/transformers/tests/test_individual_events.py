import pytest
import pytest_asyncio
import datetime
import json
import uuid
from typing import Dict, Any, List
from unittest.mock import MagicMock, patch, AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.event import Event
from app.transformers.event_transformer import EventTransformer
from app.routers.telemetry import process_event, find_matching_start_event

class TestIndividualEventProcessing:
    """Test suite for processing individual events and detecting relationships."""
    
    @pytest_asyncio.fixture
    async def mock_session(self):
        """Create a mock database session."""
        session = MagicMock(spec=AsyncSession)
        
        # Mock the execute method
        session.execute = AsyncMock()
        
        # Mock the commit method
        session.commit = AsyncMock()
        
        # Mock the flush method
        session.flush = AsyncMock()
        
        return session
    
    @pytest.fixture
    def create_mock_event(self):
        """Create a mock Event object factory."""
        def _create_event(id=1, event_type="LLM_call_start", agent_id="test-agent", data=None, timestamp=None):
            event = MagicMock()
            event.id = id
            event.event_type = event_type
            event.agent_id = agent_id
            event.data = data or {}
            event.timestamp = timestamp or datetime.datetime.now()
            event.relationship_id = None
            return event
        return _create_event
    
    @pytest.mark.asyncio
    async def test_find_matching_start_event_llm(self, mock_session, create_mock_event):
        """Test finding a matching LLM start event in the database."""
        # Create a mock finish event
        finish_event = create_mock_event(
            id=2,
            event_type="LLM_call_finish",
            data={"model": "test-model"}
        )
        
        # Create a mock start event that would be returned from the query
        start_event = create_mock_event(
            id=1,
            event_type="LLM_call_start",
            data={"model": "test-model"}
        )
        
        # Setup the mock database query response
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = start_event
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        # Call the function
        with patch('app.routers.telemetry.select', return_value=MagicMock()):
            result = await find_matching_start_event("test-agent", finish_event, mock_session)
        
        # Verify the result
        assert result is not None
        assert result.id == 1
        assert result.event_type == "LLM_call_start"
        
        # Verify the query was called with the correct parameters
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_find_matching_start_event_tool(self, mock_session, create_mock_event):
        """Test finding a matching tool start event in the database."""
        # Create a mock finish event
        finish_event = create_mock_event(
            id=2,
            event_type="call_finish",
            data={"tool_name": "get_weather"}
        )
        
        # Create a mock start event that would be returned from the query
        start_event = create_mock_event(
            id=1,
            event_type="call_start",
            data={"tool_name": "get_weather"}
        )
        
        # Setup the mock database query response
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = start_event
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        # Call the function
        with patch('app.routers.telemetry.select', return_value=MagicMock()):
            result = await find_matching_start_event("test-agent", finish_event, mock_session)
        
        # Verify the result
        assert result is not None
        assert result.id == 1
        assert result.event_type == "call_start"
        
        # Verify the query was called with the correct parameters
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_find_matching_start_event_no_match(self, mock_session, create_mock_event):
        """Test when no matching start event is found."""
        # Create a mock finish event
        finish_event = create_mock_event(
            id=2,
            event_type="LLM_call_finish",
            data={"model": "test-model"}
        )
        
        # Setup the mock database query response to return None
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = None
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        # Call the function
        with patch('app.routers.telemetry.select', return_value=MagicMock()):
            result = await find_matching_start_event("test-agent", finish_event, mock_session)
        
        # Verify the result
        assert result is None
        
        # Verify the query was called
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_find_matching_start_event_not_finish_type(self, mock_session, create_mock_event):
        """Test with an event type that is not a finish type."""
        # Create a mock event that is not a finish type
        event = create_mock_event(
            id=1,
            event_type="system_event"  # Not a finish event type
        )
        
        # Call the function
        with patch('app.routers.telemetry.select', return_value=MagicMock()):
            result = await find_matching_start_event("test-agent", event, mock_session)
        
        # Verify the result
        assert result is None
        
        # Verify the query was NOT called
        mock_session.execute.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_process_event_with_relationship(self, mock_session, create_mock_event):
        """Test processing an event and establishing a relationship."""
        # Create mock start event returned from find_matching_start_event
        start_event = create_mock_event(
            id=1,
            event_type="LLM_call_start",
            timestamp=datetime.datetime.now() - datetime.timedelta(seconds=1)
        )
        
        # Create a finish event raw data
        finish_event_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "level": "INFO",
            "agent_id": "test-agent",
            "event_type": "LLM_call_finish",
            "channel": "LLM",
            "data": {
                "model": "test-model",
                "response": "Test response"
            }
        }
        
        # Mock select and update for Event model
        with patch('app.routers.telemetry.find_matching_start_event', return_value=start_event), \
             patch('app.routers.telemetry.select', return_value=MagicMock()), \
             patch('app.routers.telemetry.update', return_value=MagicMock()), \
             patch('app.models.event.Event') as mock_event_model, \
             patch('app.models.agent.Agent') as mock_agent_model:
                
            # Mock the agent query
            agent_result = MagicMock()
            agent_scalars = MagicMock()
            agent_scalars.first.return_value = None
            agent_result.scalars.return_value = agent_scalars
            
            # Configure session.execute to return different results
            mock_session.execute.side_effect = [
                agent_result,  # First call for agent lookup
                None,          # Second call for session.flush()
                None,          # Third call for relationship update
            ]
            
            # Process the event
            await process_event(finish_event_data, mock_session)
        
        # Verify the session operations occurred
        assert mock_session.add.call_count >= 1
        mock_session.flush.assert_called_once()
        mock_session.commit.assert_called_once() 