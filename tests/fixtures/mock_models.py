"""
Mock models for testing.

This module provides mock implementations of the database models
to use in tests without requiring a real database connection.
"""

from datetime import datetime

class Agent:
    """Mock Agent model for testing."""
    
    def __init__(self, agent_id=None, name=None, llm_provider=None, first_seen=None, last_seen=None):
        self.agent_id = agent_id
        self.name = name
        self.llm_provider = llm_provider
        self.first_seen = first_seen or datetime.now()
        self.last_seen = last_seen or datetime.now()


class Session:
    """Mock Session model for testing."""
    
    def __init__(self, session_id=None, agent_id=None, start_time=None, 
                 total_events=0, total_tokens=0, total_cost=0):
        self.session_id = session_id
        self.agent_id = agent_id
        self.start_time = start_time or datetime.now()
        self.total_events = total_events
        self.total_tokens = total_tokens
        self.total_cost = total_cost


class SecurityAlert:
    """Mock SecurityAlert model for testing."""
    
    def __init__(self, event_id=None, alert_type=None, severity=None, 
                 description=None, timestamp=None):
        self.event_id = event_id
        self.alert_type = alert_type
        self.severity = severity
        self.description = description
        self.timestamp = timestamp or datetime.now()


class TokenUsage:
    """Mock TokenUsage model for testing."""
    
    def __init__(self, event_id=None, session_id=None, model=None, 
                 input_tokens=0, output_tokens=0, total_tokens=0, 
                 cost=0, timestamp=None):
        self.event_id = event_id
        self.session_id = session_id
        self.model = model
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_tokens = total_tokens
        self.cost = cost
        self.timestamp = timestamp or datetime.now()


class FrameworkDetails:
    """Mock FrameworkDetails model for testing."""
    
    def __init__(self, event_id=None, framework_name=None, 
                 framework_version=None, timestamp=None):
        self.event_id = event_id
        self.framework_name = framework_name
        self.framework_version = framework_version
        self.timestamp = timestamp or datetime.now()


class PerformanceMetric:
    """Mock PerformanceMetric model for testing."""
    
    def __init__(self, event_id=None, session_id=None, metric_type=None,
                 duration_ms=None, timestamp=None):
        self.event_id = event_id
        self.session_id = session_id
        self.metric_type = metric_type
        self.duration_ms = duration_ms
        self.timestamp = timestamp or datetime.now() 