"""
Tests for the extractors module.

This module contains tests for the extractors that normalize
complex nested JSON data from events into dedicated relational models.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
import datetime
import json

from app.business_logic.extractors.model_response_extractor import ModelResponseExtractor
from app.business_logic.extractors.model_request_extractor import ModelRequestExtractor
from app.business_logic.extractors.security_extractor import SecurityExtractor


class TestModelResponseExtractor:
    """Tests for the ModelResponseExtractor."""
    
    def test_can_process(self):
        """Test that the extractor can process model_response events."""
        # Create a mock event
        event = MagicMock()
        event.event_type = "model_response"
        
        # Create extractor
        extractor = ModelResponseExtractor()
        
        # Check that it can process the event
        assert extractor.can_process(event) is True
        
        # Test with a different event type
        event.event_type = "model_request"
        assert extractor.can_process(event) is False
    
    @pytest.mark.asyncio
    async def test_extract_token_usage(self):
        """Test extracting token usage from an event."""
        # Create a mock event with token usage data
        event = MagicMock()
        event.id = 1
        event.event_type = "model_response"
        event.data = {
            "llm_output": {
                "model": "test-model",
                "usage": {
                    "input_tokens": "29",
                    "output_tokens": "101"
                }
            }
        }
        
        # Create mock DB session
        db_session = AsyncMock()
        
        # Create extractor
        extractor = ModelResponseExtractor()
        
        # Call the method
        token_usage = await extractor._extract_token_usage(event, db_session)
        
        # Verify the result
        assert token_usage is not None
        assert token_usage.event_id == 1
        assert token_usage.input_tokens == 29
        assert token_usage.output_tokens == 101
        assert token_usage.total_tokens == 130
        assert token_usage.model == "test-model"
        
        # Verify the session was used
        db_session.add.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_extract_performance_metrics(self):
        """Test extracting performance metrics from an event."""
        # Create a mock event with performance data
        event = MagicMock()
        event.id = 1
        event.event_type = "model_response"
        event.data = {
            "performance": {
                "duration_ms": "1500.5",
                "timestamp": "2025-03-17T14:08:11.006702"
            }
        }
        
        # Create mock DB session
        db_session = AsyncMock()
        
        # Create extractor
        extractor = ModelResponseExtractor()
        
        # Call the method
        perf_metric = await extractor._extract_performance_metrics(event, db_session)
        
        # Verify the result
        assert perf_metric is not None
        assert perf_metric.event_id == 1
        assert perf_metric.duration_ms == 1500.5
        assert perf_metric.timestamp is not None
        
        # Verify the session was used
        db_session.add.assert_called_once()


class TestModelRequestExtractor:
    """Tests for the ModelRequestExtractor."""
    
    def test_can_process(self):
        """Test that the extractor can process model_request events."""
        # Create a mock event
        event = MagicMock()
        event.event_type = "model_request"
        
        # Create extractor
        extractor = ModelRequestExtractor()
        
        # Check that it can process the event
        assert extractor.can_process(event) is True
        
        # Test with a different event type
        event.event_type = "model_response"
        assert extractor.can_process(event) is False
    
    @pytest.mark.asyncio
    async def test_extract_framework_details(self):
        """Test extracting framework details from an event."""
        # Create a mock event with framework data
        event = MagicMock()
        event.id = 1
        event.event_type = "model_request"
        event.data = {
            "framework": {
                "name": "langchain",
                "version": "0.3.44",
                "components": {
                    "chain_type": "None",
                    "llm_type": "ChatAnthropic",
                    "tool_type": "None"
                }
            },
            "framework_version": "0.3.44"
        }
        
        # Create mock DB session
        db_session = AsyncMock()
        
        # Create extractor
        extractor = ModelRequestExtractor()
        
        # Call the method
        framework_details = await extractor._extract_framework_details(event, db_session)
        
        # Verify the result
        assert framework_details is not None
        assert framework_details.event_id == 1
        assert framework_details.framework_name == "langchain"
        assert framework_details.framework_version == "0.3.44"
        assert framework_details.component_name == "ChatAnthropic"
        assert framework_details.component_type == "llm_type"
        
        # Verify the session was used
        db_session.add.assert_called_once()


class TestSecurityExtractor:
    """Tests for the SecurityExtractor."""
    
    def test_can_process(self):
        """Test that the extractor can process events with security data."""
        # Create a mock event with security data
        event = MagicMock()
        event.data = {
            "security": {
                "alert_level": "none"
            }
        }
        
        # Create extractor
        extractor = SecurityExtractor()
        
        # Check that it can process the event
        assert extractor.can_process(event) is True
        
        # Test with an event without security data
        event.data = {}
        assert extractor.can_process(event) is False
    
    @pytest.mark.asyncio
    async def test_extract_security_alerts(self):
        """Test extracting security alerts from an event."""
        # Create a mock event with security data
        event = MagicMock()
        event.id = 1
        event.event_type = "model_request"
        event.data = {
            "security": {
                "alert_level": "warning",
                "field_checks": {
                    "prompts": {
                        "alert_level": "warning"
                    },
                    "metadata": {
                        "alert_level": "none"
                    }
                }
            }
        }
        
        # Create mock DB session
        db_session = AsyncMock()
        
        # Create extractor
        extractor = SecurityExtractor()
        
        # Call the method
        alerts = await extractor._extract_security_alerts(event, db_session)
        
        # Verify the result
        assert len(alerts) == 2  # One for top-level, one for prompts
        assert alerts[0].event_id == 1
        assert alerts[0].alert_level == "warning"
        assert alerts[0].field_path == ""
        assert alerts[1].event_id == 1
        assert alerts[1].alert_level == "warning"
        assert alerts[1].field_path == "prompts"
        
        # Verify the session was used
        assert db_session.add.call_count == 2 