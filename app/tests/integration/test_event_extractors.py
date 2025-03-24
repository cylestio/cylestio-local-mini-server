"""
Integration tests for event extractors.

Tests the interaction between various extractors for different event types.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch

from app.business_logic.extractors.base import extractor_registry
from app.business_logic.extractors.llm_call_extractor import LLMCallExtractor
from app.business_logic.extractors.monitor_event_extractor import MonitorEventExtractor
from app.business_logic.extractors.framework_extractor import FrameworkExtractor
# Import the custom FrameworkDetails class defined in the extractor
from app.business_logic.extractors.framework_extractor import FrameworkDetails as ExtractorFrameworkDetails
from app.models.model_details import ModelDetails
from app.models.token_usage import TokenUsage
from app.models.performance_metric import PerformanceMetric
from app.models.security_alert import SecurityAlert
from app.models.session import Session
from app.models.framework_details import FrameworkDetails


class TestEventExtractorsIntegration:
    """Integration tests for event extractors."""
    
    @pytest.fixture
    def mock_event_llm_call_start(self):
        """Create a mock LLM_call_start event for testing."""
        event = MagicMock()
        event.id = "test-event-id-1"
        event.event_type = "LLM_call_start"
        event.timestamp = datetime.now()
        event.agent_id = "test-agent"
        # Add duration_ms attribute to handle PerformanceExtractor checks
        event.duration_ms = None
        event.data = {
            "method": "messages.create",
            "prompt": [
                {"role": "user", "content": "Tell me about AI"}
            ],
            "alert": "suspicious"
        }
        return event
    
    @pytest.fixture
    def mock_event_llm_call_finish(self):
        """Create a mock LLM_call_finish event for testing."""
        event = MagicMock()
        event.id = "test-event-id-2"
        event.event_type = "LLM_call_finish"
        event.timestamp = datetime.now()
        event.agent_id = "test-agent"
        # Add duration_ms attribute to handle PerformanceExtractor checks
        event.duration_ms = None
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
    def mock_event_monitor_init(self):
        """Create a mock monitor_init event for testing."""
        event = MagicMock()
        event.id = "test-event-id-3"
        event.event_type = "monitor_init"
        event.timestamp = datetime.now()
        event.agent_id = "test-agent"
        # Add duration_ms attribute to handle PerformanceExtractor checks
        event.duration_ms = None
        event.data = {
            "timestamp": datetime.now().isoformat(),
            "api_endpoint": "https://api.example.com",
            "log_file": "output/test_monitoring.json",
            "llm_provider": "Anthropic",
            "debug_level": "INFO",
            "development_mode": True
        }
        return event
    
    @pytest.fixture
    def mock_event_framework_patch(self):
        """Create a mock framework_patch event for testing."""
        event = MagicMock()
        event.id = "test-event-id-4"
        event.event_type = "framework_patch"
        event.timestamp = datetime.now()
        event.agent_id = "rag-agent"
        # Add duration_ms attribute to handle PerformanceExtractor checks
        event.duration_ms = None
        event.data = {
            "framework": {
                "name": "langchain",
                "component": "ChatAnthropic",
                "version": "0.3.44"
            },
            "version": "0.3.44",
            "patch_time": "2025-03-20T22:44:50.457640",
            "method": "ChatAnthropic._generate",
            "note": "Using simple wrapper approach to avoid internal method dependencies",
            "agent_id": "rag-agent"
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
        # Using MagicMock instead of actual Session to avoid ORM errors
        mock_session = MagicMock()
        mock_session.agent_id = "test-agent"
        mock_session.start_time = datetime.now()
        mock_session.session_id = "test-session-123"
        mock_session.session_metadata = {}
        
        mock_first.return_value = mock_session
        
        return session
    
    @pytest.mark.asyncio
    async def test_registry_finds_correct_extractors(self):
        """Test that the registry returns the correct extractors for event types."""
        # Test LLM_call_start event
        llm_start_event = MagicMock()
        llm_start_event.event_type = "LLM_call_start"
        llm_start_event.duration_ms = None  # Handle PerformanceExtractor check
        llm_start_event.data = {}
        extractors = extractor_registry.get_extractors_for_event(llm_start_event)
        assert any(isinstance(extractor, LLMCallExtractor) for extractor in extractors)
        
        # Test monitor_init event
        monitor_init_event = MagicMock()
        monitor_init_event.event_type = "monitor_init"
        monitor_init_event.duration_ms = None  # Handle PerformanceExtractor check
        monitor_init_event.data = {}
        extractors = extractor_registry.get_extractors_for_event(monitor_init_event)
        assert any(isinstance(extractor, MonitorEventExtractor) for extractor in extractors)
        
        # Test framework_patch event
        framework_patch_event = MagicMock()
        framework_patch_event.event_type = "framework_patch"
        framework_patch_event.duration_ms = None  # Handle PerformanceExtractor check
        framework_patch_event.data = {"framework": {}}
        extractors = extractor_registry.get_extractors_for_event(framework_patch_event)
        assert any(isinstance(extractor, FrameworkExtractor) for extractor in extractors)
    
    @pytest.mark.asyncio
    async def test_llm_call_start_processing(self, mock_event_llm_call_start, mock_db_session):
        """Test processing of LLM_call_start events through the registry."""
        # Get extractors that can process this event
        extractors = [ext for ext in extractor_registry.get_all_extractors() 
                     if ext.can_process(mock_event_llm_call_start)]
        
        # Verify that the LLMCallExtractor is among them
        assert any(isinstance(extractor, LLMCallExtractor) for extractor in extractors)
        
        # Process the event with all capable extractors
        for extractor in extractors:
            if isinstance(extractor, LLMCallExtractor):
                await extractor.process(mock_event_llm_call_start, mock_db_session)
        
        # Verify that at least two objects were added (model details and security alert)
        assert mock_db_session.add.call_count >= 2
        
        # Check that at least one security alert was added
        security_alert_added = False
        for call in mock_db_session.add.call_args_list:
            args = call[0]
            if isinstance(args[0], SecurityAlert):
                security_alert_added = True
                assert args[0].event_id == mock_event_llm_call_start.id
                assert args[0].alert_type == "suspicious"
                assert args[0].severity == "medium"
                
        assert security_alert_added, "No SecurityAlert was added to the session"
    
    @pytest.mark.asyncio
    async def test_llm_call_finish_processing(self, mock_event_llm_call_finish, mock_db_session):
        """Test processing of LLM_call_finish events through the registry."""
        # Get extractors that can process this event
        extractors = [ext for ext in extractor_registry.get_all_extractors() 
                     if ext.can_process(mock_event_llm_call_finish)]
        
        # Verify that the LLMCallExtractor is among them
        assert any(isinstance(extractor, LLMCallExtractor) for extractor in extractors)
        
        # Process the event with all capable extractors
        for extractor in extractors:
            if isinstance(extractor, LLMCallExtractor):
                await extractor.process(mock_event_llm_call_finish, mock_db_session)
        
        # Verify that at least three objects were added (model details, token usage, and performance metrics)
        assert mock_db_session.add.call_count >= 3
        
        # Check for specific objects
        token_usage_added = False
        performance_metric_added = False
        model_details_added = False
        
        for call in mock_db_session.add.call_args_list:
            args = call[0]
            if isinstance(args[0], TokenUsage):
                token_usage_added = True
                assert args[0].event_id == mock_event_llm_call_finish.id
                assert args[0].input_tokens == 10
                assert args[0].output_tokens == 50
                assert args[0].total_tokens == 60
                
            elif isinstance(args[0], PerformanceMetric):
                performance_metric_added = True
                assert args[0].event_id == mock_event_llm_call_finish.id
                assert args[0].duration_ms == 1250.5
                
            elif isinstance(args[0], ModelDetails):
                model_details_added = True
                assert args[0].event_id == mock_event_llm_call_finish.id
                assert args[0].model_name == "claude-3-haiku-20240307"
                assert args[0].model_provider == "Anthropic"
        
        assert token_usage_added, "No TokenUsage was added to the session"
        assert performance_metric_added, "No PerformanceMetric was added to the session"
        assert model_details_added, "No ModelDetails was added to the session"
    
    @pytest.mark.asyncio
    @patch('app.business_logic.extractors.monitor_event_extractor.Session')
    async def test_monitor_init_processing(self, mock_session_class, mock_event_monitor_init, mock_db_session):
        """Test processing of monitor_init events directly with a MonitorEventExtractor."""
        # Setup mock Session class to return a mock object when instantiated
        mock_session_instance = MagicMock()
        mock_session_instance.agent_id = mock_event_monitor_init.agent_id
        mock_session_instance.session_metadata = {}
        mock_session_class.return_value = mock_session_instance
        
        # Create a direct instance of the extractor
        extractor = MonitorEventExtractor()
        
        # Make sure it can process this event type
        assert extractor.can_process(mock_event_monitor_init) is True
        
        # Process the event
        await extractor.process(mock_event_monitor_init, mock_db_session)
        
        # Verify a Session was created and added to the database
        mock_session_class.assert_called_once()
        mock_db_session.add.assert_called_with(mock_session_instance)
    
    @pytest.mark.asyncio
    async def test_framework_patch_processing(self, mock_event_framework_patch, mock_db_session):
        """Test processing of framework_patch events directly with a FrameworkExtractor."""
        # Create a direct instance of the extractor
        extractor = FrameworkExtractor()
        
        # Make sure it can process this event type
        assert extractor.can_process(mock_event_framework_patch) is True
        
        # Process the event
        details = await extractor._extract_framework_details(mock_event_framework_patch)
        
        # Verify the details were extracted correctly
        assert isinstance(details, ExtractorFrameworkDetails)
        assert details.event_id == mock_event_framework_patch.id
        assert details.framework_name == "langchain"
        assert details.framework_version == "0.3.44"
        assert details.component_name == "ChatAnthropic"
        assert details.component_type == "framework_component"
        assert details.metadata["method_name"] == "ChatAnthropic._generate"
        
        # Reset the mock to ensure we're only counting new calls
        mock_db_session.add.reset_mock()
        
        # Now test the full process method
        await extractor.process(mock_event_framework_patch, mock_db_session)
        
        # Verify that the framework details were added to the session
        assert mock_db_session.add.called
    
    @pytest.mark.asyncio
    @patch('app.business_logic.extractors.monitor_event_extractor.Session')
    async def test_all_event_types_with_direct_extractors(self, mock_session_class, 
                                                       mock_event_llm_call_start, 
                                                       mock_event_llm_call_finish, 
                                                       mock_event_monitor_init, 
                                                       mock_event_framework_patch, 
                                                       mock_db_session):
        """Test processing of all event types with direct extractor instances."""
        # Setup mock Session class
        mock_session_instance = MagicMock()
        mock_session_instance.agent_id = "test-agent"
        mock_session_instance.session_metadata = {}
        mock_session_class.return_value = mock_session_instance
        
        # Create direct instances of extractors
        llm_extractor = LLMCallExtractor()
        monitor_extractor = MonitorEventExtractor()
        framework_extractor = FrameworkExtractor()
        
        # Reset mock to ensure clean state
        mock_db_session.add.reset_mock()
        
        # Process each event with its appropriate extractor
        await llm_extractor.process(mock_event_llm_call_start, mock_db_session)
        await llm_extractor.process(mock_event_llm_call_finish, mock_db_session)
        await monitor_extractor.process(mock_event_monitor_init, mock_db_session)
        await framework_extractor.process(mock_event_framework_patch, mock_db_session)
        
        # Verify that multiple objects were added
        assert mock_db_session.add.call_count >= 5  # At least 5 objects should be added
        
        # Verify that Session was created
        mock_session_class.assert_called_once() 