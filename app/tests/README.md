# Cylestio Test Environment Guide

This document explains how to use the Cylestio test environment, particularly focusing on database configuration for different types of tests.

## Database Configuration for Tests

The test environment supports two database configurations:

1. **In-Memory SQLite** - For unit tests that need to be fast and isolated
2. **File-Based SQLite** - For integration tests that need persistence between runs

### Environment Variables

The test environment is controlled by several environment variables:

| Variable | Description | Default | 
|----------|-------------|---------|
| `CYLESTIO_TEST_MODE` | Indicates the app is running in test mode | `true` in test environment |
| `CYLESTIO_TEST_DB_TYPE` | Database type: `memory` or `file` | `file` |
| `CYLESTIO_DB_PATH` | Path to the database file | `./data/test_cylestio.db` |
| `CYLESTIO_PRESERVE_TEST_DB` | Whether to preserve the database after tests | `true` |
| `CYLESTIO_RESET_TEST_DB` | Whether to reset tables before tests | `false` |

## Test Types and Fixtures

### Unit Tests with In-Memory Database

Unit tests use an in-memory SQLite database that is created and destroyed for each test. This provides isolation and speed.

**Example usage:**

```python
import pytest
import pytest_asyncio

@pytest.mark.asyncio
async def test_something(unit_test_session):
    """Test using in-memory database."""
    # Use the unit_test_session for database operations
    result = await unit_test_session.execute(...)
    # Assert on results
```

**Key fixtures:**

- `setup_unit_test_env` - Sets up the in-memory database environment
- `setup_unit_test_db` - Creates tables in the in-memory database
- `unit_test_session` - Provides a session for database operations
- `unit_test_client` - Provides a TestClient for API testing

### Integration Tests with File-Based Database

Integration tests use a file-based SQLite database that can be preserved between test runs. This is useful for:

1. Debugging issues by examining the database after tests
2. Testing data persistence across multiple test runs
3. Long-running integration tests that need to maintain state

**Example usage:**

```python
import pytest
import pytest_asyncio

@pytest.mark.asyncio
async def test_something(integration_test_session):
    """Test using file-based database."""
    # Use the integration_test_session for database operations
    result = await integration_test_session.execute(...)
    # Assert on results
```

**Key fixtures:**

- `setup_integration_test_env` - Sets up the file-based database environment
- `setup_integration_test_db` - Creates tables in the file-based database
- `integration_test_session` - Provides a session for database operations
- `integration_test_client` - Provides a TestClient for API testing

## Database Persistence

The file-based database can be preserved after tests for inspection and debugging.

By default, the database is located at `./data/test_cylestio.db` (relative to the project root).

You can examine this database using:

1. **SQLite Browser**: Install [DB Browser for SQLite](https://sqlitebrowser.org/) and open the database file
2. **SQLite CLI**: Run `sqlite3 ./data/test_cylestio.db`

## Example: Examining Test Data

After running integration tests, you can examine the data in the preserved database:

```sql
-- List all agents created during tests
SELECT * FROM agents WHERE agent_id LIKE 'test-agent-%';

-- View events for a specific agent
SELECT * FROM events WHERE agent_id = 'test-agent-123';

-- Count events by type
SELECT event_type, COUNT(*) FROM events GROUP BY event_type;
```

## Test Examples

### Example 1: Basic Unit Test

```python
async def test_agent_creation(unit_test_session):
    """Test creating an agent in the database."""
    # Create a test agent
    agent = Agent(
        agent_id="test-agent-123",
        first_seen=datetime.now(),
        last_seen=datetime.now(),
        llm_provider="Test Provider"
    )
    unit_test_session.add(agent)
    await unit_test_session.commit()
    
    # Query the agent
    result = await unit_test_session.execute(
        text("SELECT * FROM agents WHERE agent_id = 'test-agent-123'")
    )
    saved_agent = result.fetchone()
    
    # Assertions
    assert saved_agent is not None
    assert saved_agent.agent_id == "test-agent-123"
```

### Example 2: Integration Test with Database Preservation

```python
async def test_telemetry_flow(integration_test_session, integration_test_client):
    """Test the full telemetry flow with database persistence."""
    # Send telemetry event
    test_event = {
        "agent_id": "test-agent-456",
        "event_type": "test_event",
        "timestamp": datetime.now().isoformat(),
        "level": "INFO",
        "channel": "test-channel",
        "data": {"message": "Test event"}
    }
    
    response = integration_test_client.post("/api/v1/telemetry", json=test_event)
    assert response.status_code == 202
    
    # Wait for processing
    await asyncio.sleep(1)
    
    # Verify the event was stored
    result = await integration_test_session.execute(
        text("SELECT * FROM events WHERE agent_id = 'test-agent-456'")
    )
    events = result.fetchall()
    
    assert len(events) > 0
    
    # The database file is preserved at ./data/test_cylestio.db
    # and can be examined after the test completes
```

## Troubleshooting

### Common Issues

1. **Database file not found**: Ensure the data directory exists and has write permissions
2. **Tables not created**: Check test_config.py and init_db.py for proper initialization
3. **Test conflicts**: Ensure tests don't interfere with each other's data

### Inspecting the Test Database

After running integration tests, you can use the following command to inspect the database:

```bash
sqlite3 ./data/test_cylestio.db
```

Useful SQLite commands:
```
.tables                   # List all tables
.schema events            # Show schema for events table
SELECT * FROM agents;     # List all agents
.quit                     # Exit SQLite
```

## Best Practices

1. Use unit tests with in-memory database for testing isolated components
2. Use integration tests with file-based database for testing full flows
3. Clear data at the beginning of each test to avoid test dependencies
4. Use unique identifiers for test data to avoid conflicts
5. Don't rely on data created by other tests unless explicitly testing persistence 