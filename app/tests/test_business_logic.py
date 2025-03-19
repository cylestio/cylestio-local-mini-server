"""
Test script for the business logic layer.

This script tests the functionality of the business logic layer by calculating metrics
and extracting insights from example data.
"""
import os
import sys
import json
from datetime import datetime, timedelta

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
    db = create_test_db()
    
    print("\n=== Available Metrics ===")
    metrics = business_logic.get_available_metrics()
    for metric in metrics:
        print(f"- {metric}")
    
    print("\n=== Calculating All Metrics ===")
    all_metrics = business_logic.calculate_all_metrics(db)
    
    # Print summary of each metric
    for name, result in all_metrics.items():
        print(f"\n--- {name} ---")
        if isinstance(result, dict):
            # Print the top-level keys and some basic info
            print(f"Keys: {', '.join(result.keys())}")
            
            # Print more detailed information for specific metrics
            if name.endswith('ResponseTimeMetricCalculator'):
                if 'average_response_time_ms' in result:
                    print(f"Average Response Time: {result['average_response_time_ms']:.2f} ms")
            
            elif name.endswith('TokenUsageMetricCalculator'):
                if 'total_tokens' in result:
                    print(f"Total Tokens: {result['total_tokens']}")
                if 'average_tokens_per_request' in result:
                    print(f"Avg Tokens/Request: {result['average_tokens_per_request']}")
            
            elif name.endswith('ErrorRateMetricCalculator'):
                if 'error_rate' in result:
                    print(f"Error Rate: {result['error_rate']:.2f}%")
                if 'total_errors' in result:
                    print(f"Total Errors: {result['total_errors']}")
        else:
            print(f"Result: {result}")
    
    return db


def test_insights(db):
    """Test insights extraction."""
    print("\n=== Available Insights ===")
    insights = business_logic.get_available_insights()
    for insight in insights:
        print(f"- {insight}")
    
    print("\n=== Extracting All Insights ===")
    all_insights = business_logic.extract_all_insights(db)
    
    # Print summary of each insight
    for name, result in all_insights.items():
        print(f"\n--- {name} ---")
        if isinstance(result, dict):
            # Print the top-level keys
            print(f"Keys: {', '.join(result.keys())}")
            
            # Print more detailed information for specific insights
            if name.endswith('AgentHealthInsightExtractor'):
                if 'overall_health' in result:
                    print(f"Overall Health Score: {result['overall_health']['score']}")
                    print(f"Health Status: {result['overall_health']['status']}")
            
            elif name.endswith('ConversationQualityInsightExtractor'):
                if 'session_insights' in result:
                    sessions = len(result['session_insights'])
                    print(f"Analyzed Sessions: {sessions}")
                if 'agent_insights' in result:
                    agents = len(result['agent_insights'])
                    print(f"Analyzed Agents: {agents}")
            
            elif name.endswith('ContentUsageInsightExtractor'):
                if 'model_usage' in result and 'models' in result['model_usage']:
                    models = list(result['model_usage']['models'].keys())
                    print(f"Models Used: {', '.join(models)}")
        else:
            print(f"Result: {result}")


if __name__ == "__main__":
    db = test_metrics()
    test_insights(db)
    print("\nBusiness logic layer tests completed successfully!") 