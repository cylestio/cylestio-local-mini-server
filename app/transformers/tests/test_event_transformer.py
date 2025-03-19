import pytest
import datetime
import json
import uuid
from typing import Dict, Any, List

from app.transformers.event_transformer import EventTransformer

class TestEventTransformer:
    """Test suite for the event transformer."""
    
    @pytest.fixture
    def transformer(self):
        """Return an EventTransformer instance."""
        return EventTransformer()
    
    def test_transform_llm_call_start(self, transformer):
        """Test transforming an LLM call start event."""
        # Sample LLM call start event
        raw_event = {
            "timestamp": "2025-03-18T18:57:14.557916Z",
            "level": "INFO",
            "agent_id": "weather-agent",
            "event_type": "LLM_call_start",
            "channel": "LLM",
            "caller": {
                "file": "events_listener.py",
                "line": 107,
                "function": "sync_wrapper"
            },
            "data": {
                "prompt": '[{"role": "user", "content": "hi"}]',
                "alert": "none"
            }
        }
        
        # Transform the event
        transformed = transformer.transform(raw_event)
        
        # Verify basic fields
        assert transformed["event_type"] == "LLM_call_start"
        assert transformed["agent_id"] == "weather-agent"
        assert transformed["channel"] == "LLM"
        assert transformed["direction"] == "outgoing"
        
        # Verify transformed data
        assert "parsed_prompt" in transformed["data"]
        assert transformed["data"]["alert_level"] == "none"
        
        # Verify caller information
        assert transformed["caller_file"] == "events_listener.py"
        assert transformed["caller_line"] == 107
        assert transformed["caller_function"] == "sync_wrapper"
    
    def test_transform_llm_call_finish(self, transformer):
        """Test transforming an LLM call finish event."""
        # Sample LLM call finish event
        raw_event = {
            "timestamp": "2025-03-18T18:57:16.013121Z",
            "level": "INFO",
            "agent_id": "weather-agent",
            "event_type": "LLM_call_finish",
            "channel": "LLM",
            "caller": {
                "file": "events_listener.py",
                "line": 121,
                "function": "sync_wrapper"
            },
            "data": {
                "duration": 1.4553089141845703,
                "response": "Hello! How can I assist you today?",
                "alert": "none",
                "model": "claude-3-haiku-20240307",
                "usage": {
                    "prompt_tokens": None,
                    "completion_tokens": None,
                    "total_tokens": None
                }
            }
        }
        
        # Transform the event
        transformed = transformer.transform(raw_event)
        
        # Verify basic fields
        assert transformed["event_type"] == "LLM_call_finish"
        assert transformed["agent_id"] == "weather-agent"
        assert transformed["channel"] == "LLM"
        assert transformed["direction"] == "incoming"
        
        # Verify transformed data
        assert transformed["duration_ms"] == pytest.approx(1455.3089141845703)
        assert transformed["data"]["response_text"] == "Hello! How can I assist you today?"
        assert transformed["data"]["model"] == "claude-3-haiku-20240307"
        assert transformed["data"]["alert_level"] == "none"
    
    def test_transform_tool_call_start(self, transformer):
        """Test transforming a tool call start event."""
        # Sample tool call start event
        raw_event = {
            "timestamp": "2025-03-18T18:57:21.346465Z",
            "level": "INFO",
            "agent_id": "weather-agent",
            "event_type": "call_start",
            "channel": "MCP",
            "caller": {
                "file": "events_listener.py",
                "line": 33,
                "function": "async_wrapper"
            },
            "data": {
                "function": "call_tool",
                "args": "(<mcp.client.session.ClientSession object at 0x1070781d0>, 'get_forecast', {'latitude': 37.7749, 'longitude': -122.4194})",
                "kwargs": "{}"
            }
        }
        
        # Transform the event
        transformed = transformer.transform(raw_event)
        
        # Verify basic fields
        assert transformed["event_type"] == "call_start"
        assert transformed["agent_id"] == "weather-agent"
        assert transformed["channel"] == "MCP"
        assert transformed["direction"] == "outgoing"
        
        # Verify transformed data
        assert transformed["data"]["tool_name"] == "call_tool"
        assert "tool_function" in transformed["data"]
        assert transformed["data"]["tool_function"] == "get_forecast"
    
    def test_transform_tool_call_finish(self, transformer):
        """Test transforming a tool call finish event."""
        # Sample tool call finish event
        raw_event = {
            "timestamp": "2025-03-18T18:57:21.586600Z",
            "level": "INFO",
            "agent_id": "weather-agent",
            "event_type": "call_finish",
            "channel": "MCP",
            "caller": {
                "file": "events_listener.py",
                "line": 36,
                "function": "async_wrapper"
            },
            "data": {
                "function": "call_tool",
                "duration": 0.24011993408203125,
                "result": "meta=None content=[TextContent(type='text', text='\\nToday:\\nTemperature: 60\\u00b0F\\nWind: 5 to 10 mph NW\\nForecast: Sunny.', annotations=None)] isError=False"
            }
        }
        
        # Transform the event
        transformed = transformer.transform(raw_event)
        
        # Verify basic fields
        assert transformed["event_type"] == "call_finish"
        assert transformed["agent_id"] == "weather-agent"
        assert transformed["channel"] == "MCP"
        assert transformed["direction"] == "incoming"
        
        # Verify transformed data
        assert transformed["duration_ms"] == pytest.approx(240.11993408203125)
        assert transformed["data"]["tool_name"] == "call_tool"
        assert "tool_result" in transformed["data"]
        assert "is_error" in transformed["data"]
    
    def test_transform_security_event(self, transformer):
        """Test transforming a security event."""
        # Sample security event
        raw_event = {
            "timestamp": "2025-03-18T18:57:25.642100Z",
            "level": "WARNING",
            "agent_id": "weather-agent",
            "event_type": "LLM_call_blocked",
            "channel": "LLM",
            "caller": {
                "file": "weather_client.py",
                "line": 121,
                "function": "process_query"
            },
            "data": {
                "reason": "dangerous prompt",
                "prompt": '[{"role": "user", "content": "drop"}]'
            }
        }
        
        # Transform the event
        transformed = transformer.transform(raw_event)
        
        # Verify basic fields
        assert transformed["event_type"] == "LLM_call_blocked"
        assert transformed["agent_id"] == "weather-agent"
        assert transformed["level"] == "WARNING"
        
        # Verify transformed data
        assert transformed["data"]["security_reason"] == "dangerous prompt"
        assert "affected_content" in transformed["data"]
    
    def test_transform_system_event(self, transformer):
        """Test transforming a system event."""
        # Sample system event
        raw_event = {
            "timestamp": "2025-03-18T18:57:11.620036Z",
            "level": "INFO",
            "agent_id": "weather-agent",
            "event_type": "MCP_patch",
            "channel": "SYSTEM",
            "caller": {
                "file": "weather_client.py",
                "line": 53,
                "function": "__init__"
            },
            "data": {
                "message": "MCP client patched"
            }
        }
        
        # Transform the event
        transformed = transformer.transform(raw_event)
        
        # Verify basic fields
        assert transformed["event_type"] == "MCP_patch"
        assert transformed["agent_id"] == "weather-agent"
        assert transformed["channel"] == "SYSTEM"
        
        # Verify transformed data
        assert transformed["data"]["system_message"] == "MCP client patched"
        assert transformed["data"]["patch_type"] == "MCP"
    
    def test_process_batch_with_relationships(self, transformer):
        """Test processing a batch of events with relationship detection."""
        # Create a batch of related events
        start_time = datetime.datetime(2025, 3, 18, 18, 57, 14, 557916)
        finish_time = datetime.datetime(2025, 3, 18, 18, 57, 16, 13121)
        
        # LLM call start
        llm_start = {
            "timestamp": start_time.isoformat() + "Z",
            "level": "INFO",
            "agent_id": "test-agent",
            "event_type": "LLM_call_start",
            "channel": "LLM",
            "data": {
                "prompt": '[{"role": "user", "content": "test"}]',
                "alert": "none"
            }
        }
        
        # LLM call finish
        llm_finish = {
            "timestamp": finish_time.isoformat() + "Z",
            "level": "INFO",
            "agent_id": "test-agent",
            "event_type": "LLM_call_finish",
            "channel": "LLM",
            "data": {
                "response": "This is a test response",
                "model": "test-model"
            }
        }
        
        # Process the batch
        batch = [llm_start, llm_finish]
        transformed_batch = transformer.process_batch(batch)
        
        # Check that there are two events
        assert len(transformed_batch) == 2
        
        # Check that the events are related
        assert transformed_batch[0]["direction"] == "outgoing"
        assert transformed_batch[1]["direction"] == "incoming"
        
        # Check that both events have the same relationship ID
        assert "relationship_id" in transformed_batch[0]
        assert "relationship_id" in transformed_batch[1]
        assert transformed_batch[0]["relationship_id"] == transformed_batch[1]["relationship_id"]
        
        # Check that duration was calculated
        assert "duration_ms" in transformed_batch[1]
        expected_duration = (finish_time - start_time).total_seconds() * 1000
        assert transformed_batch[1]["duration_ms"] == pytest.approx(expected_duration) 