"""
Unit tests for usage metrics calculators.
"""

import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, UTC
from sqlalchemy import func

from app.business_logic.metrics.usage_metrics import (
    FrameworkUsageCalculator,
    ModelUsageCalculator,
    AgentUsageCalculator,
    SessionCountCalculator,
    EventTypeDistributionCalculator,
    ChannelDistributionCalculator
)


class TestFrameworkUsageCalculator(unittest.TestCase):
    """Tests for the FrameworkUsageCalculator class."""
    
    def setUp(self):
        """Set up test data for each test."""
        self.calculator = FrameworkUsageCalculator()
        self.mock_db = MagicMock()
        
        # Mock the query results for framework usage
        self.framework_counts = [
            ("langchain", 10),
            ("llamaindex", 7),
            ("custom", 5),
            ("autogen", 3),
            ("crewai", 2)
        ]
        
        # Setup the mock query chain
        self.mock_query = self.mock_db.query.return_value
        self.mock_query.join.return_value = self.mock_query
        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.group_by.return_value = self.mock_query
        self.mock_query.order_by.return_value = self.mock_query
        self.mock_query.all.return_value = self.framework_counts
    
    def test_calculate_framework_usage(self):
        """Test calculation of framework usage metrics."""
        # Calculate metrics
        metrics = self.calculator.calculate(self.mock_db)
        
        # Verify metrics
        self.assertEqual(metrics["total_events"], 27)  # 10 + 7 + 5 + 3 + 2
        
        # Verify framework distribution
        expected_distribution = {
            "langchain": 10,
            "llamaindex": 7,
            "custom": 5,
            "autogen": 3,
            "crewai": 2
        }
        self.assertEqual(metrics["framework_distribution"], expected_distribution)
        
        # Verify top frameworks
        expected_top_frameworks = [
            ("langchain", 10),
            ("llamaindex", 7),
            ("custom", 5),
            ("autogen", 3),
            ("crewai", 2)
        ]
        self.assertEqual(metrics["top_frameworks"], expected_top_frameworks)


class TestModelUsageCalculator(unittest.TestCase):
    """Tests for the ModelUsageCalculator class."""
    
    def setUp(self):
        """Set up test data for each test."""
        self.calculator = ModelUsageCalculator()
        self.mock_db = MagicMock()
        
        # Mock the query results for model usage
        self.model_counts = [
            ("gpt-4", 15),
            ("claude-3-opus", 10),
            ("gpt-3.5-turbo", 8),
            ("llama-3-70b", 5),
            ("claude-3-sonnet", 4)
        ]
        
        # Setup the mock query chain
        self.mock_query = self.mock_db.query.return_value
        self.mock_query.join.return_value = self.mock_query
        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.group_by.return_value = self.mock_query
        self.mock_query.order_by.return_value = self.mock_query
        self.mock_query.all.return_value = self.model_counts
    
    def test_calculate_model_usage(self):
        """Test calculation of model usage metrics."""
        # Calculate metrics
        metrics = self.calculator.calculate(self.mock_db)
        
        # Verify metrics
        self.assertEqual(metrics["total_events"], 42)  # 15 + 10 + 8 + 5 + 4
        
        # Verify model distribution
        expected_distribution = {
            "gpt-4": 15,
            "claude-3-opus": 10,
            "gpt-3.5-turbo": 8,
            "llama-3-70b": 5,
            "claude-3-sonnet": 4
        }
        self.assertEqual(metrics["model_distribution"], expected_distribution)
        
        # Verify top models
        expected_top_models = [
            ("gpt-4", 15),
            ("claude-3-opus", 10),
            ("gpt-3.5-turbo", 8),
            ("llama-3-70b", 5),
            ("claude-3-sonnet", 4)
        ]
        self.assertEqual(metrics["top_models"], expected_top_models)


class TestAgentUsageCalculator(unittest.TestCase):
    """Tests for the AgentUsageCalculator class."""
    
    def setUp(self):
        """Set up test data for each test."""
        self.calculator = AgentUsageCalculator()
        self.mock_db = MagicMock()
        
        # Mock the query results for agent usage
        self.agent_counts = [
            ("agent-1", 20),
            ("agent-2", 15),
            ("agent-3", 10),
            ("agent-4", 8),
            ("agent-5", 5)
        ]
        
        # Setup the mock query chain
        self.mock_query = self.mock_db.query.return_value
        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.group_by.return_value = self.mock_query
        self.mock_query.order_by.return_value = self.mock_query
        self.mock_query.all.return_value = self.agent_counts
    
    def test_calculate_agent_usage(self):
        """Test calculation of agent usage metrics."""
        # Calculate metrics
        metrics = self.calculator.calculate(self.mock_db)
        
        # Verify metrics
        self.assertEqual(metrics["total_events"], 58)  # 20 + 15 + 10 + 8 + 5
        
        # Verify agent distribution
        expected_distribution = {
            "agent-1": 20,
            "agent-2": 15,
            "agent-3": 10,
            "agent-4": 8,
            "agent-5": 5
        }
        self.assertEqual(metrics["agent_distribution"], expected_distribution)
        
        # Verify top agents
        expected_top_agents = [
            ("agent-1", 20),
            ("agent-2", 15),
            ("agent-3", 10),
            ("agent-4", 8),
            ("agent-5", 5)
        ]
        self.assertEqual(metrics["top_agents"], expected_top_agents)


class TestSessionCountCalculator(unittest.TestCase):
    """Tests for the SessionCountCalculator class."""
    
    def setUp(self):
        """Set up test data for each test."""
        self.calculator = SessionCountCalculator()
        self.mock_db = MagicMock()
        
        # Mock the query results for session counts
        self.session_data = [
            ("session-1", "agent-1", 10),
            ("session-2", "agent-1", 12),
            ("session-3", "agent-2", 8),
            ("session-4", "agent-2", 15),
            ("session-5", "agent-3", 20)
        ]
        
        # Setup the mock query chain
        self.mock_query = self.mock_db.query.return_value
        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.group_by.return_value = self.mock_query
        self.mock_query.all.return_value = self.session_data
    
    def test_calculate_session_counts(self):
        """Test calculation of session count metrics."""
        # Calculate metrics
        metrics = self.calculator.calculate(self.mock_db)
        
        # Verify metrics
        self.assertEqual(metrics["total_sessions"], 5)
        
        # Verify average events per session
        event_counts = [10, 12, 8, 15, 20]
        expected_avg = sum(event_counts) / len(event_counts)
        self.assertEqual(metrics["average_events_per_session"], expected_avg)
        
        # Verify sessions by agent
        expected_sessions_by_agent = {
            "agent-1": 2,
            "agent-2": 2,
            "agent-3": 1
        }
        self.assertEqual(metrics["sessions_by_agent"], expected_sessions_by_agent)


class TestEventTypeDistributionCalculator(unittest.TestCase):
    """Tests for the EventTypeDistributionCalculator class."""
    
    def setUp(self):
        """Set up test data for each test."""
        self.calculator = EventTypeDistributionCalculator()
        self.mock_db = MagicMock()
        
        # Mock the query results for event type distribution
        self.event_type_counts = [
            ("model_response", 30),
            ("user_message", 25),
            ("system_event", 15),
            ("error", 10),
            ("debug", 5)
        ]
        
        # Setup the mock query chain
        self.mock_query = self.mock_db.query.return_value
        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.group_by.return_value = self.mock_query
        self.mock_query.order_by.return_value = self.mock_query
        self.mock_query.all.return_value = self.event_type_counts
    
    def test_calculate_event_type_distribution(self):
        """Test calculation of event type distribution metrics."""
        # Calculate metrics
        metrics = self.calculator.calculate(self.mock_db)
        
        # Verify metrics
        self.assertEqual(metrics["total_events"], 85)  # 30 + 25 + 15 + 10 + 5
        
        # Verify event type distribution
        expected_distribution = {
            "model_response": 30,
            "user_message": 25,
            "system_event": 15,
            "error": 10,
            "debug": 5
        }
        self.assertEqual(metrics["event_type_distribution"], expected_distribution)
        
        # Verify top event types
        expected_top_event_types = [
            ("model_response", 30),
            ("user_message", 25),
            ("system_event", 15),
            ("error", 10),
            ("debug", 5)
        ]
        self.assertEqual(metrics["top_event_types"], expected_top_event_types)


class TestChannelDistributionCalculator(unittest.TestCase):
    """Tests for the ChannelDistributionCalculator class."""
    
    def setUp(self):
        """Set up test data for each test."""
        self.calculator = ChannelDistributionCalculator()
        self.mock_db = MagicMock()
        
        # Mock the query results for channel distribution
        self.channel_counts = [
            ("web", 40),
            ("api", 30),
            ("cli", 20),
            ("integration", 10)
        ]
        
        # Setup the mock query chain
        self.mock_query = self.mock_db.query.return_value
        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.group_by.return_value = self.mock_query
        self.mock_query.order_by.return_value = self.mock_query
        self.mock_query.all.return_value = self.channel_counts
    
    def test_calculate_channel_distribution(self):
        """Test calculation of channel distribution metrics."""
        # Calculate metrics
        metrics = self.calculator.calculate(self.mock_db)
        
        # Verify metrics
        self.assertEqual(metrics["total_events"], 100)  # 40 + 30 + 20 + 10
        
        # Verify channel distribution
        expected_distribution = {
            "web": 40,
            "api": 30,
            "cli": 20,
            "integration": 10
        }
        self.assertEqual(metrics["channel_distribution"], expected_distribution)


if __name__ == "__main__":
    unittest.main() 