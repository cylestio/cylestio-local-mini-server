import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from datetime import datetime, timedelta, timezone
import json
from sqlalchemy import select
import uuid

from app.main import app
from app.models.agent import Agent
from app.models.event import Event
from app.database.init_db import init_db

# Test data
TEST_EVENT_TYPES = ["model_response", "user_input", "tool_call", "system_error"]
TEST_CHANNELS = ["llm", "user", "system"]
TEST_LEVELS = ["INFO", "DEBUG", "ERROR", "CRITICAL"]

@pytest_asyncio.fixture
async def generate_test_data(async_session):
    """Generate test data for API tests."""
    # Create test agent with unique ID for each test
    agent_id = f"test-agent-{uuid.uuid4()}"
    agent = Agent(
        agent_id=agent_id,
        first_seen=datetime.now(timezone.utc) - timedelta(days=7),
        last_seen=datetime.now(timezone.utc),
        llm_provider="test-provider"
    )
    async_session.add(agent)
    await async_session.flush()
    
    # Create events for the agent
    base_time = datetime.now(timezone.utc) - timedelta(days=3)
    events = []
    for i in range(50):
        # Mix of event types, channels, and levels
        event_type = TEST_EVENT_TYPES[i % len(TEST_EVENT_TYPES)]
        channel = TEST_CHANNELS[i % len(TEST_CHANNELS)]
        level = TEST_LEVELS[i % len(TEST_LEVELS)]
        
        # Create events with timestamps spread over the last 3 days
        timestamp = base_time + timedelta(hours=i)
        
        # Add some duration for performance metrics
        duration_ms = 100 + (i * 5) if event_type == "model_response" else None
        
        event = Event(
            timestamp=timestamp,
            level=level,
            agent_id=agent_id,
            event_type=event_type,
            channel=channel,
            direction="inbound" if i % 2 == 0 else "outbound",
            session_id=f"session-{i // 10}",
            relationship_id=f"rel-{i // 5}" if i % 5 == 0 else None,
            data={"test_key": f"test_value_{i}"},
            duration_ms=duration_ms,
            caller_file="test_file.py",
            caller_line=i + 100,
            caller_function="test_function"
        )
        async_session.add(event)
        events.append(event)
    
    await async_session.commit()
    
    # Return the agent ID and list of events
    return {"agent_id": agent_id, "events": events}

@pytest.mark.asyncio
async def test_list_agents(generate_test_data, test_client):
    """Test listing agents endpoint."""
    agent_id = generate_test_data["agent_id"]
    
    response = test_client.get("/api/v1/agents/")
    assert response.status_code == 200
    
    data = response.json()
    assert "results" in data
    assert "pagination" in data
    assert len(data["results"]) >= 1
    
    # Verify the test agent is in the results
    test_agent = next((a for a in data["results"] if a["agent_id"] == agent_id), None)
    assert test_agent is not None
    assert "first_seen" in test_agent
    assert "last_seen" in test_agent
    assert "status" in test_agent

@pytest.mark.asyncio
async def test_get_agent_details(generate_test_data, test_client):
    """Test getting agent details endpoint."""
    agent_id = generate_test_data["agent_id"]
    
    response = test_client.get(f"/api/v1/agents/{agent_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["agent_id"] == agent_id
    assert "event_counts" in data
    assert "performance" in data
    assert "latest_event" in data
    assert "first_event" in data

@pytest.mark.asyncio
async def test_get_agent_events(generate_test_data, test_client):
    """Test getting agent events endpoint."""
    agent_id = generate_test_data["agent_id"]
    
    response = test_client.get(f"/api/v1/agents/{agent_id}/events")
    assert response.status_code == 200
    
    data = response.json()
    assert "results" in data
    assert "pagination" in data
    assert len(data["results"]) > 0
    
    # Test filtering
    response = test_client.get(
        f"/api/v1/agents/{agent_id}/events",
        params={"event_type": "model_response", "limit": 5}
    )
    assert response.status_code == 200
    
    data = response.json()
    assert all(e["event_type"] == "model_response" for e in data["results"])
    assert len(data["results"]) <= 5

@pytest.mark.asyncio
async def test_get_agent_event(generate_test_data, test_client):
    """Test getting a specific agent event."""
    agent_id = generate_test_data["agent_id"]
    event_id = generate_test_data["events"][0].id
    
    response = test_client.get(f"/api/v1/agents/{agent_id}/events/{event_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == event_id
    assert data["agent_id"] == agent_id
    assert "timestamp" in data
    assert "level" in data
    assert "event_type" in data

@pytest.mark.asyncio
async def test_get_agent_metrics(generate_test_data, test_client):
    """Test getting agent metrics endpoint."""
    agent_id = generate_test_data["agent_id"]
    
    # Test performance metrics
    response = test_client.get(
        f"/api/v1/agents/{agent_id}/metrics",
        params={"metric_type": "performance"}
    )
    assert response.status_code == 200
    
    data = response.json()
    assert "metrics" in data
    assert data["metrics"]["type"] == "performance"
    assert "overall" in data["metrics"]
    assert "time_series" in data["metrics"]
    
    # Test usage metrics
    response = test_client.get(
        f"/api/v1/agents/{agent_id}/metrics",
        params={"metric_type": "usage"}
    )
    assert response.status_code == 200
    
    data = response.json()
    assert "metrics" in data
    assert data["metrics"]["type"] == "usage"
    
    # Test error metrics
    response = test_client.get(
        f"/api/v1/agents/{agent_id}/metrics",
        params={"metric_type": "errors"}
    )
    assert response.status_code == 200
    
    data = response.json()
    assert "metrics" in data
    assert data["metrics"]["type"] == "errors"

@pytest.mark.asyncio
async def test_get_alerts(generate_test_data, test_client):
    """Test getting alerts endpoint."""
    response = test_client.get("/api/v1/alerts/")
    assert response.status_code == 200
    
    data = response.json()
    assert "results" in data
    assert "pagination" in data

@pytest.mark.asyncio
async def test_get_alert_details(generate_test_data, test_client, async_session):
    """Test getting a specific alert."""
    agent_id = generate_test_data["agent_id"]
    
    # Find an error event ID to use as alert ID
    error_events = [e for e in generate_test_data["events"] if e.level in ["ERROR", "CRITICAL"]]
    
    if error_events:
        alert_id = error_events[0].id
        response = test_client.get(f"/api/v1/alerts/{alert_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == alert_id
        assert "severity" in data
        assert "status" in data
        assert "context" in data 