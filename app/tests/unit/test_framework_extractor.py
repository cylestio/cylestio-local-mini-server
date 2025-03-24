"""
Unit test for FrameworkExtractor.

Tests the extraction of data from framework_patch and related events.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch

from app.business_logic.extractors.framework_extractor import FrameworkExtractor
# Import the FrameworkDetails class directly from the extractor module
from app.business_logic.extractors.framework_extractor import FrameworkDetails


class TestFrameworkExtractor:
    """Tests for the FrameworkExtractor."""
    
    @pytest.fixture
    def extractor(self):
        """Create a FrameworkExtractor instance for testing."""
        return FrameworkExtractor()
    
    @pytest.fixture
    def mock_event_patch(self):
        """Create a mock framework_patch event for testing."""
        event = MagicMock()
        event.id = "test-event-id-1"
        event.event_type = "framework_patch"
        event.timestamp = datetime.now()
        event.agent_id = "test-agent"
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
    def mock_event_with_components(self):
        """Create a mock event with components information."""
        event = MagicMock()
        event.id = "test-event-id-2"
        event.event_type = "model_request"
        event.timestamp = datetime.now()
        event.agent_id = "test-agent"
        event.data = {
            "components": {
                "chain_type": "None",
                "llm_type": "ChatAnthropic",
                "tool_type": "None"
            },
            "version": "0.3.44"
        }
        return event
    
    @pytest.fixture
    def mock_event_plain_framework(self):
        """Create a mock event with simple framework information."""
        event = MagicMock()
        event.id = "test-event-id-3"
        event.event_type = "model_request"
        event.timestamp = datetime.now()
        event.agent_id = "test-agent"
        event.data = {
            "framework": "langchain",
            "version": "0.3.44"
        }
        return event
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        session.add = AsyncMock()
        return session
    
    def test_can_process(self, extractor, mock_event_patch, mock_event_with_components, mock_event_plain_framework):
        """Test that the extractor can identify framework events."""
        # Should process framework_patch events
        assert extractor.can_process(mock_event_patch) is True
        
        # Should process events with components data
        assert extractor.can_process(mock_event_with_components) is True
        
        # Should process events with plain framework field
        assert extractor.can_process(mock_event_plain_framework) is True
        
        # Should not process other event types without framework data
        other_event = MagicMock()
        other_event.event_type = "some_other_event"
        other_event.data = {"some_field": "some_value"}
        assert extractor.can_process(other_event) is False
    
    @pytest.mark.asyncio
    async def test_extract_framework_details_from_patch(self, extractor, mock_event_patch):
        """Test extracting framework details from a framework_patch event."""
        # Extract details
        details = await extractor._extract_framework_details(mock_event_patch)
        
        # Verify the extracted details
        assert isinstance(details, FrameworkDetails)
        assert details.event_id == mock_event_patch.id
        assert details.framework_name == "langchain"
        assert details.framework_version == "0.3.44"
        assert details.component_name == "ChatAnthropic"
        assert details.component_type == "framework_component"
        assert details.metadata["method_name"] == "ChatAnthropic._generate"
        assert details.metadata["patch_time"] == "2025-03-20T22:44:50.457640"
        assert details.metadata["note"] == "Using simple wrapper approach to avoid internal method dependencies"
    
    @pytest.mark.asyncio
    async def test_extract_framework_from_components(self, extractor, mock_event_with_components):
        """Test extracting framework details from components field."""
        # Extract details
        details = await extractor._extract_framework_details(mock_event_with_components)
        
        # Verify the extracted details
        assert isinstance(details, FrameworkDetails)
        assert details.event_id == mock_event_with_components.id
        assert details.framework_version == "unknown"  # The extractor doesn't extract version from components
        assert details.component_name == "ChatAnthropic"
        assert details.component_type == "llm_type"
    
    @pytest.mark.asyncio
    async def test_extract_plain_framework(self, extractor, mock_event_plain_framework):
        """Test extracting framework details from plain framework field."""
        # Extract details
        details = await extractor._extract_framework_details(mock_event_plain_framework)
        
        # Verify the extracted details
        assert isinstance(details, FrameworkDetails)
        assert details.event_id == mock_event_plain_framework.id
        assert details.framework_name == "langchain"
        assert details.framework_version == "unknown"  # The extractor doesn't extract version from data["version"]
    
    @pytest.mark.asyncio
    async def test_extract_with_method_name(self):
        """Test method name extraction and class inference."""
        # Create a mock event with only method name
        event = MagicMock()
        event.id = "test-event-id-4"
        event.event_type = "framework_patch"
        event.data = {
            "method": "ChatOpenAI.generate_content",
            "framework": {
                "name": "langchain",
                "version": "0.3.44"
            }
        }
        
        # Extract details
        extractor = FrameworkExtractor()
        details = await extractor._extract_framework_details(event)
        
        # Verify the component name is extracted from method
        assert details.component_name == "ChatOpenAI"
        assert details.component_type == "patched_class"
        assert details.metadata["method_name"] == "ChatOpenAI.generate_content"
    
    @pytest.mark.asyncio
    async def test_process_method(self, extractor, mock_event_patch, mock_db_session):
        """Test the main process method."""
        # Process the event
        await extractor.process(mock_event_patch, mock_db_session)
        
        # Verify that a framework details was added to the session
        assert mock_db_session.add.called
        
        # Get the framework details that was added
        call_args = mock_db_session.add.call_args
        framework_details = call_args[0][0]
        
        # Verify the framework details fields
        assert isinstance(framework_details, FrameworkDetails)
        assert framework_details.event_id == mock_event_patch.id
        assert framework_details.framework_name == "langchain"
    
    @pytest.mark.asyncio
    async def test_process_with_error(self, extractor, mock_db_session):
        """Test error handling in the process method."""
        # Create a mock event that will cause an error
        bad_event = MagicMock()
        bad_event.id = "test-event-id-5"
        bad_event.event_type = "framework_patch"
        bad_event.data = None  # This will cause an error
        
        # Process the event - should not raise exception
        await extractor.process(bad_event, mock_db_session)
        
        # Verify that nothing was added to the session
        assert not mock_db_session.add.called
    
    @pytest.mark.asyncio
    async def test_extract_complex_components(self):
        """Test extraction of components from nested structure."""
        # Create a mock event with nested components
        event = MagicMock()
        event.id = "test-event-id-6"
        event.event_type = "framework_patch"
        event.data = {
            "framework": {
                "name": "langchain",
                "version": "0.3.44",
                "components": {
                    "llm": "ChatGPT",
                    "retriever": "Chroma",
                    "memory": "BufferMemory"
                }
            }
        }
        
        # Extract details
        extractor = FrameworkExtractor()
        details = await extractor._extract_framework_details(event)
        
        # Verify the components_json field contains the nested components
        assert isinstance(details.components_json, dict)
        assert details.components_json["llm"] == "ChatGPT"
        assert details.components_json["retriever"] == "Chroma"
        assert details.components_json["memory"] == "BufferMemory" 