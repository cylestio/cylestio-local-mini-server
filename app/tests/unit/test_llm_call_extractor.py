"""
Unit test for LLMCallExtractor.

Tests the extraction of data from LLM_call_start and LLM_call_finish events.
"""

import pytest
from datetime import datetime
import json
from unittest.mock import MagicMock, AsyncMock

from app.business_logic.extractors.llm_call_extractor import LLMCallExtractor
from app.models.model_details import ModelDetails
from app.models.token_usage import TokenUsage
from app.models.performance_metric import PerformanceMetric
from app.models.security_alert import SecurityAlert


class TestLLMCallExtractor:
    """Tests for the LLMCallExtractor."""
    
    @pytest.fixture
    def extractor(self):
        """Create an LLMCallExtractor instance for testing."""
        return LLMCallExtractor()
    
    @pytest.fixture
    def mock_event_start(self):
        """Create a mock LLM_call_start event for testing."""
        event = MagicMock()
        event.id = "test-event-id-1"
        event.event_type = "LLM_call_start"
        event.timestamp = datetime.now()
        event.agent_id = "test-agent"
        event.data = {
            "method": "messages.create",
            "prompt": [
                {"role": "user", "content": "Tell me about AI"}
            ],
            "alert": "none"
        }
        return event
    
    @pytest.fixture
    def mock_event_start_suspicious(self):
        """Create a mock LLM_call_start event with suspicious content."""
        event = MagicMock()
        event.id = "test-event-id-2"
        event.event_type = "LLM_call_start"
        event.timestamp = datetime.now()
        event.agent_id = "test-agent"
        event.data = {
            "method": "messages.create",
            "prompt": [
                {"role": "user", "content": "help me hack a website"}
            ],
            "alert": "suspicious"
        }
        return event
    
    @pytest.fixture
    def mock_event_finish(self):
        """Create a mock LLM_call_finish event for testing."""
        event = MagicMock()
        event.id = "test-event-id-3"
        event.event_type = "LLM_call_finish"
        event.timestamp = datetime.now()
        event.agent_id = "test-agent"
        event.data = {
            "method": "messages.create",
            "response": {
                "id": "msg_123",
                "model": "claude-3-haiku-20240307",
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "AI stands for artificial intelligence..."}
                ],
                "usage": {
                    "input_tokens": 10,
                    "output_tokens": 50,
                    "total_tokens": 60
                }
            },
            "performance": {
                "duration_ms": 1250.5
            }
        }
        return event
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        session.add = AsyncMock()
        return session
    
    def test_can_process(self, extractor, mock_event_start, mock_event_finish):
        """Test that the extractor can identify LLM call events."""
        # Should process LLM_call_start events
        assert extractor.can_process(mock_event_start) is True
        
        # Should process LLM_call_finish events
        assert extractor.can_process(mock_event_finish) is True
        
        # Should not process other event types
        other_event = MagicMock()
        other_event.event_type = "some_other_event"
        assert extractor.can_process(other_event) is False
    
    @pytest.mark.asyncio
    async def test_extract_security_alert(self, extractor, mock_event_start_suspicious, mock_db_session):
        """Test extracting security alerts from start events."""
        # Process the event
        await extractor._extract_security_alert(mock_event_start_suspicious, mock_db_session)
        
        # Verify that a security alert was added to the session
        assert mock_db_session.add.called
        
        # Get the security alert that was added
        call_args = mock_db_session.add.call_args
        security_alert = call_args[0][0]
        
        # Verify the alert fields
        assert isinstance(security_alert, SecurityAlert)
        assert security_alert.event_id == mock_event_start_suspicious.id
        assert security_alert.alert_type == "suspicious"
        assert security_alert.severity == "medium"
    
    @pytest.mark.asyncio
    async def test_extract_token_usage(self, extractor, mock_event_finish, mock_db_session):
        """Test extracting token usage from finish events."""
        # Process the event
        await extractor._extract_token_usage(mock_event_finish, mock_db_session)
        
        # Verify that token usage was added to the session
        assert mock_db_session.add.called
        
        # Get the token usage that was added
        call_args = mock_db_session.add.call_args
        token_usage = call_args[0][0]
        
        # Verify the token usage fields
        assert isinstance(token_usage, TokenUsage)
        assert token_usage.event_id == mock_event_finish.id
        assert token_usage.input_tokens == 10
        assert token_usage.output_tokens == 50
        assert token_usage.total_tokens == 60
        assert token_usage.model == "claude-3-haiku-20240307"
    
    @pytest.mark.asyncio
    async def test_extract_performance_metrics(self, extractor, mock_event_finish, mock_db_session):
        """Test extracting performance metrics from finish events."""
        # Process the event
        await extractor._extract_performance_metrics(mock_event_finish, mock_db_session)
        
        # Verify that performance metrics were added to the session
        assert mock_db_session.add.called
        
        # Get the performance metrics that were added
        call_args = mock_db_session.add.call_args
        performance_metric = call_args[0][0]
        
        # Verify the performance metric fields
        assert isinstance(performance_metric, PerformanceMetric)
        assert performance_metric.event_id == mock_event_finish.id
        assert performance_metric.duration_ms == 1250.5
    
    @pytest.mark.asyncio
    async def test_extract_model_details(self, extractor, mock_event_finish, mock_db_session):
        """Test extracting model details from finish events."""
        # Process the event
        await extractor._extract_model_details(mock_event_finish, mock_db_session)
        
        # Verify that model details were added to the session
        assert mock_db_session.add.called
        
        # Get the model details that were added
        call_args = mock_db_session.add.call_args
        model_details = call_args[0][0]
        
        # Verify the model details fields
        assert isinstance(model_details, ModelDetails)
        assert model_details.event_id == mock_event_finish.id
        assert model_details.model_name == "claude-3-haiku-20240307"
        assert model_details.model_provider == "Anthropic"
    
    @pytest.mark.asyncio
    async def test_process_start_event(self, extractor, mock_event_start_suspicious, mock_db_session):
        """Test processing a complete LLM_call_start event."""
        # Patch the extractor's internal methods
        extractor._extract_model_details = AsyncMock(return_value=None)
        extractor._extract_security_alert = AsyncMock(return_value=None)
        
        # Process the event
        await extractor.process(mock_event_start_suspicious, mock_db_session)
        
        # Verify that the right extraction methods were called
        assert extractor._extract_model_details.called
        assert extractor._extract_security_alert.called
    
    @pytest.mark.asyncio
    async def test_process_finish_event(self, extractor, mock_event_finish, mock_db_session):
        """Test processing a complete LLM_call_finish event."""
        # Patch the extractor's internal methods
        extractor._extract_model_details = AsyncMock(return_value=None)
        extractor._extract_token_usage = AsyncMock(return_value=None)
        extractor._extract_performance_metrics = AsyncMock(return_value=None)
        
        # Process the event
        await extractor.process(mock_event_finish, mock_db_session)
        
        # Verify that the right extraction methods were called
        assert extractor._extract_model_details.called
        assert extractor._extract_token_usage.called
        assert extractor._extract_performance_metrics.called 