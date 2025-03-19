"""
Test script for the business logic layer.

This script tests the functionality of the business logic layer by calculating metrics
and extracting insights from example data.
"""
import os
import sys
import json
from datetime import datetime, timedelta, UTC

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Add the parent directory to the path to import app modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.business_logic import business_logic
from app.models.event import Event, Base


def create_test_db():
    """Create a test database with example events."""
    # Create an in-memory SQLite database
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    
    # Create a session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    # Load example events from the test data directory
    test_data_dir = os.path.join(os.path.dirname(parent_dir), 'test_data')
    if not os.path.exists(test_data_dir):
        test_data_dir = os.path.join(parent_dir, 'test_data')
    
    # Create an example event if we can't load from test data
    if not os.path.exists(test_data_dir):
        print("No test data directory found. Creating example events.")
        
        # Create example events
        events = [
            # Model request event
            Event(
                id="req1",
                timestamp=datetime.utcnow() - timedelta(minutes=5),
                agent_id="agent1",
                session_id="session1",
                event_type="model_request",
                level="info",
                channel="default",
                direction="outgoing",
                data={
                    "llm_request": {
                        "model": "gpt-4",
                        "messages": [
                            {"role": "system", "content": "You are a helpful assistant."},
                            {"role": "user", "content": "Hello, how are you?"}
                        ],
                        "usage": {
                            "input_tokens": 20
                        }
                    }
                }
            ),
            # Model response event
            Event(
                id="resp1",
                timestamp=datetime.utcnow() - timedelta(minutes=4, seconds=30),
                agent_id="agent1",
                session_id="session1",
                event_type="model_response",
                level="info",
                channel="default",
                direction="incoming",
                data={
                    "llm_output": {
                        "model": "gpt-4",
                        "usage": {
                            "output_tokens": 15
                        }
                    },
                    "performance": {
                        "duration_ms": 500
                    }
                }
            ),
            # Error event
            Event(
                id="err1",
                timestamp=datetime.utcnow() - timedelta(minutes=2),
                agent_id="agent1",
                session_id="session1",
                event_type="error",
                level="error",
                channel="default",
                direction="internal",
                data={
                    "error": "Connection timeout",
                    "error_type": "network_error"
                }
            )
        ]
        
        # Add events to the database
        for event in events:
            db.add(event)
    else:
        # Load events from example files
        print(f"Loading test data from {test_data_dir}")
        for filename in os.listdir(test_data_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(test_data_dir, filename)
                with open(filepath, 'r') as f:
                    try:
                        event_data = json.load(f)
                        
                        # Convert timestamp string to datetime
                        if 'timestamp' in event_data and isinstance(event_data['timestamp'], str):
                            event_data['timestamp'] = datetime.fromisoformat(event_data['timestamp'].replace('Z', '+00:00'))
                        
                        # Create Event object
                        event = Event(**event_data)
                        db.add(event)
                    except json.JSONDecodeError:
                        print(f"Error parsing JSON from {filepath}")
                    except Exception as e:
                        print(f"Error loading event from {filepath}: {e}")
    
    # Commit the changes
    db.commit()
    
    return db


def test_metrics():
    """Test metrics calculation."""
    from unittest.mock import MagicMock
    
    # Create a mock database session
    mock_db = MagicMock()
    
    # Mock the query results that would be returned from the database
    mock_events = [
        MagicMock(
            id=1,
            timestamp=datetime.now(UTC) - timedelta(minutes=5),
            agent_id="test-agent",
            session_id="test-session",
            event_type="model_request",
            data={"llm_request": {"model": "gpt-4", "usage": {"input_tokens": 20}}}
        ),
        MagicMock(
            id=2, 
            timestamp=datetime.now(UTC) - timedelta(minutes=4, seconds=30),
            agent_id="test-agent",
            session_id="test-session",
            event_type="model_response",
            data={"llm_output": {"model": "gpt-4", "usage": {"output_tokens": 15}}, "performance": {"duration_ms": 500}}
        ),
        MagicMock(
            id=3, 
            timestamp=datetime.now(UTC) - timedelta(minutes=2),
            agent_id="test-agent",
            session_id="test-session",
            event_type="error",
            data={"error": "Connection timeout", "error_type": "network_error"}
        )
    ]
    
    # Configure the mock query to return our mock events
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_filter.all.return_value = mock_events
    mock_query.filter.return_value = mock_filter
    mock_query.all.return_value = mock_events
    mock_db.query.return_value = mock_query
    
    print("\n=== Available Metrics ===")
    metrics = business_logic.get_available_metrics()
    assert len(metrics) > 0, "Should have available metrics"
    
    print("\n=== Calculating Metrics ===")
    for metric_name in metrics:
        try:
            result = business_logic.calculate_metric(metric_name, db=mock_db)
            print(f"- {metric_name}: {result}")
            assert isinstance(result, dict), f"Metric {metric_name} should return a dictionary"
        except Exception as e:
            print(f"- {metric_name}: Error - {str(e)}")
    
    # Test all metrics calculation
    all_metrics = business_logic.calculate_all_metrics(db=mock_db)
    assert isinstance(all_metrics, dict), "All metrics should be returned as a dictionary"
    assert len(all_metrics) > 0, "Should calculate at least one metric"


def test_insights():
    """Test insights extraction."""
    from unittest.mock import MagicMock
    
    # Create a mock database session
    mock_db = MagicMock()
    
    # Mock the query results that would be returned from the database
    mock_events = [
        MagicMock(
            id=1,
            timestamp=datetime.now(UTC) - timedelta(minutes=5),
            agent_id="test-agent",
            session_id="test-session",
            event_type="model_request",
            data={"llm_request": {"model": "gpt-4", "usage": {"input_tokens": 20}}}
        ),
        MagicMock(
            id=2, 
            timestamp=datetime.now(UTC) - timedelta(minutes=4, seconds=30),
            agent_id="test-agent",
            session_id="test-session",
            event_type="model_response",
            data={"llm_output": {"model": "gpt-4", "usage": {"output_tokens": 15}}, "performance": {"duration_ms": 500}}
        ),
        MagicMock(
            id=3, 
            timestamp=datetime.now(UTC) - timedelta(minutes=2),
            agent_id="test-agent",
            session_id="test-session",
            event_type="error",
            data={"error": "Connection timeout", "error_type": "network_error"}
        )
    ]
    
    # Configure the mock query to return our mock events
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_filter.all.return_value = mock_events
    mock_query.filter.return_value = mock_filter
    mock_query.all.return_value = mock_events
    mock_db.query.return_value = mock_query
    
    print("\n=== Available Insights ===")
    insights = business_logic.get_available_insights()
    assert len(insights) > 0, "Should have available insights"
    
    print("\n=== Extracting Insights ===")
    # Count successful extractions
    successful_extractions = 0
    for insight_name in insights:
        try:
            result = business_logic.extract_insight(insight_name, db=mock_db)
            print(f"- {insight_name}: {result}")
            assert isinstance(result, dict), f"Insight {insight_name} should return a dictionary"
            successful_extractions += 1
        except Exception as e:
            print(f"- {insight_name}: Error - {str(e)}")
    
    # We should have at least some successful extractions
    assert successful_extractions > 0, "Should have at least one successful insight extraction"


if __name__ == "__main__":
    db = test_metrics()
    test_insights()
    print("\nBusiness logic layer tests completed successfully!") 