"""
Event fixtures for testing.

This module provides sample events to use in tests.
"""

from datetime import datetime

class MockEvent:
    """A mock event for testing."""
    
    def __init__(self, id=None, timestamp=None, level=None, agent_id=None, 
                 event_type=None, channel=None, session_id=None, data=None, 
                 direction=None, duration_ms=None, alert=None):
        self.id = id or 1
        self.timestamp = timestamp or datetime.now()
        self.level = level or "INFO"
        self.agent_id = agent_id or "test-agent-id"
        self.event_type = event_type or "TEST_EVENT"
        self.channel = channel or "TEST"
        self.session_id = session_id or "test-session-id"
        self.data = data or {}
        self.direction = direction
        self.duration_ms = duration_ms
        self.alert = alert


# Sample Model Request Event
MODEL_REQUEST_EVENT = MockEvent(
    id=1001,
    timestamp=datetime.now(),
    level="INFO",
    agent_id="test-agent-id",
    event_type="MODEL_REQUEST_EVENT",
    channel="MODEL",
    session_id="test-session-id",
    data={
        "model": "gpt-4",
        "prompt": "Hello, how are you?",
        "max_tokens": 2048,
        "temperature": 0.7,
        "caller": {
            "file": "/app/example.py",
            "line": 42,
            "function": "ask_question"
        }
    },
    direction="outgoing"
)

# Sample Model Response Event
MODEL_RESPONSE_EVENT = MockEvent(
    id=1002,
    timestamp=datetime.now(),
    level="INFO",
    agent_id="test-agent-id",
    event_type="MODEL_RESPONSE_EVENT",
    channel="MODEL",
    session_id="test-session-id",
    data={
        "model": "gpt-4",
        "completion": "I'm doing well, thank you! How can I assist you today?",
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 14,
            "total_tokens": 24
        }
    },
    direction="incoming",
    duration_ms=1250.5
)

# Sample LLM Call Start Event
LLM_CALL_START_EVENT = MockEvent(
    id=1003,
    timestamp=datetime.now(),
    level="INFO",
    agent_id="test-agent-id",
    event_type="LLM_CALL_START_EVENT",
    channel="LLM",
    session_id="test-session-id",
    data={
        "llm_type": "openai",
        "model": "gpt-4",
        "prompt": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Tell me about AI safety."}
        ]
    },
    direction="outgoing",
    alert="dangerous",
    duration_ms=None
)

# Sample LLM Call Finish Event
LLM_CALL_FINISH_EVENT = MockEvent(
    id=1004,
    timestamp=datetime.now(),
    level="INFO",
    agent_id="test-agent-id",
    event_type="LLM_CALL_FINISH_EVENT",
    channel="LLM",
    session_id="test-session-id",
    data={
        "llm_type": "openai",
        "model": "gpt-4",
        "response": "AI safety is the field of research focused on ensuring that artificial intelligence systems remain beneficial to humanity...",
        "token_usage": {
            "input_tokens": 25,
            "output_tokens": 150,
            "total_tokens": 175
        }
    },
    direction="incoming",
    duration_ms=2500.75
)

# Sample Framework Patch Event
FRAMEWORK_PATCH_EVENT = MockEvent(
    id=1007,
    timestamp=datetime.now(),
    level="INFO",
    agent_id="test-agent-id",
    event_type="FRAMEWORK_PATCH_EVENT",
    channel="FRAMEWORK",
    session_id="test-session-id",
    data={
        "framework": {
            "name": "langchain",
            "version": "0.3.44",
            "component": "ChatOpenAI"
        },
        "patch_time": datetime.now().isoformat(),
        "method": "ChatOpenAI._generate"
    }
)

# Sample Monitor Init Event
MONITOR_INIT_EVENT = MockEvent(
    id=1005,
    timestamp=datetime.now(),
    level="INFO",
    agent_id="test-agent-id",
    event_type="MONITOR_INIT_EVENT",
    channel="MONITOR",
    session_id="test-session-id",
    data={
        "framework": "cylestio",
        "version": "0.1.0",
        "llm_provider": "openai",
        "environment": "development"
    }
)

# Sample Call Finish Event
CALL_FINISH_EVENT = MockEvent(
    id=1006,
    timestamp=datetime.now(),
    level="INFO",
    agent_id="test-agent-id",
    event_type="CALL_FINISH_EVENT",
    channel="CALL",
    session_id="test-session-id",
    data={
        "function": "retrieve_documents",
        "result_count": 5,
        "elapsed_time": 350.25
    },
    duration_ms=350.25
) 