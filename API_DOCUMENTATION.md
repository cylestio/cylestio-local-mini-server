# Cylestio Metrics API Documentation

This document provides information about the available API endpoints in the Cylestio Mini-Local Server for retrieving telemetry metrics and event data.

## API Base URL

All API endpoints are prefixed with:

```
http://localhost:8000/api/v1
```

## Authentication

The API currently does not require authentication for local usage.

## Common Query Parameters

Most endpoints accept the following common query parameters:

| Parameter    | Type      | Description                                         | Example                    |
|--------------|-----------|-----------------------------------------------------|----------------------------|
| `start_time` | ISO 8601  | Start time for querying data (default: 24h ago)     | `2025-03-20T00:00:00.000Z` |
| `end_time`   | ISO 8601  | End time for querying data (default: now)           | `2025-03-21T00:00:00.000Z` |
| `agent_id`   | string    | Filter results by agent ID                          | `agent-123`                |
| `session_id` | string    | Filter results by session ID                        | `session-456`              |

## Available Endpoints

### Health Check

- **GET** `/health`

  Returns the current status of the API.

  **Response:**
  ```json
  {
    "status": "ok",
    "version": "1.0.0"
  }
  ```

### Events

- **GET** `/events`

  Retrieves telemetry events based on query parameters.

  **Response:**
  ```json
  {
    "events": [
      {
        "id": "evt-123",
        "timestamp": "2025-03-20T12:34:56.789Z",
        "agent_id": "agent-123",
        "event_type": "model_request",
        "data": { ... }
      },
      ...
    ],
    "total": 10,
    "page": 1,
    "page_size": 50
  }
  ```

- **POST** `/events`

  Creates a new telemetry event.

  **Request Body:**
  ```json
  {
    "timestamp": "2025-03-21T12:34:56.789Z",
    "agent_id": "agent-123",
    "event_type": "model_request",
    "level": "info",
    "channel": "langchain",
    "data": { ... }
  }
  ```

### Metrics

- **GET** `/metrics/token_usage/total`

  Returns total token usage metrics.

  **Response:**
  ```json
  {
    "data": {
      "input_tokens": 10000,
      "output_tokens": 5000,
      "total_tokens": 15000
    },
    "metadata": {
      "start_time": "2025-03-20T00:00:00.000Z",
      "end_time": "2025-03-21T00:00:00.000Z"
    }
  }
  ```

- **GET** `/metrics/response_time/average`

  Returns average response time metrics.

  **Response:**
  ```json
  {
    "data": {
      "average_ms": 350,
      "min_ms": 100,
      "max_ms": 750,
      "response_count": 120
    },
    "metadata": {
      "start_time": "2025-03-20T00:00:00.000Z",
      "end_time": "2025-03-21T00:00:00.000Z"
    }
  }
  ```

- **GET** `/metrics/security/alerts/count`

  Returns security alert metrics.

  **Response:**
  ```json
  {
    "data": {
      "alert_count": 5,
      "by_severity": {
        "low": 2,
        "medium": 2,
        "high": 1,
        "critical": 0
      }
    },
    "metadata": {
      "start_time": "2025-03-20T00:00:00.000Z",
      "end_time": "2025-03-21T00:00:00.000Z"
    }
  }
  ```

## Error Responses

All API endpoints return standard HTTP status codes along with a JSON error response:

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "The requested resource was not found",
    "details": { ... }
  }
}
```

## Example Usage with cURL

```bash
# Get events for a specific agent
curl "http://localhost:8000/api/v1/events?agent_id=agent-123&start_time=2025-03-20T00:00:00Z"

# Get total token usage metrics
curl "http://localhost:8000/api/v1/metrics/token_usage/total"

# Create a new event
curl -X POST "http://localhost:8000/api/v1/events" \
  -H "Content-Type: application/json" \
  -d '{"timestamp": "2025-03-21T12:34:56.789Z", "agent_id": "agent-123", "event_type": "model_request", "level": "info", "data": {"test": true}}'
```

## Example Usage with Python

```python
import requests
from datetime import datetime, timedelta

# Set up base URL and parameters
base_url = "http://localhost:8000/api/v1"
params = {
    "start_time": (datetime.now() - timedelta(days=7)).isoformat(),
    "end_time": datetime.now().isoformat(),
    "agent_id": "agent-123"
}

# Get token usage metrics
response = requests.get(f"{base_url}/metrics/token_usage/total", params=params)
data = response.json()
print(f"Total tokens: {data['data']['total_tokens']}")
``` 