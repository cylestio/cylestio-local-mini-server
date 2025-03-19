# Cylestio Mini-Local Server

A lightweight server for collecting, storing, and querying Cylestio monitoring data.

## Architecture

- **Python Monitoring SDK** sends telemetry via REST API to Mini-Local Server
- **Mini-Local Server** processes and stores data in SQLite database
- **Dashboard** queries the Mini-Local Server via REST API

## Project Structure

```
cylestio-local-mini-server/
├── app/
│   ├── database/        - Database connection and utilities
│   ├── models/          - SQLAlchemy models
│   ├── routers/         - API route handlers
│   └── tests/           - Unit and integration tests
├── data/                - SQLite database file (created at runtime)
├── input_json_records_examples/ - Sample JSON data for testing
└── dashboard_screens_examples/ - Dashboard UI examples
```

## Setup and Installation

1. Clone the repository:
   ```
   git clone https://github.com/cylestio/cylestio-local-mini-server.git
   cd cylestio-local-mini-server
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Initialize the database with sample data (optional):
   ```
   python -m app.tests.test_db_setup
   ```

## Running the Server

Start the development server:
```
uvicorn app.main:app --reload
```

The server will be available at http://localhost:8000.

API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Agents

- `GET /api/agents` - List all agents
- `GET /api/agents/{agent_id}` - Get detailed information about a specific agent
- `GET /api/agents/{agent_id}/summary` - Get summary statistics for a specific agent

### Events

- `POST /api/events` - Create a new event
- `GET /api/events` - List events with filtering options
- `GET /api/events/{event_id}` - Get a specific event by ID

### Dashboard

- `GET /api/dashboard/overview` - Get overview statistics
- `GET /api/dashboard/timeseries` - Get time series data for events
- `GET /api/dashboard/sessions` - Get session information
- `GET /api/dashboard/performance` - Get performance metrics

## Database Schema

The system uses SQLAlchemy Core with SQLite for data storage. Key tables:

- **agents** - Information about monitored agents
- **events** - Telemetry events from agents
- **sessions** - Conversation sessions and interactions

## Running Tests

Run unit tests:
```
python -m unittest discover app/tests
```

## Design Decisions

1. **Async FastAPI**: Used for non-blocking I/O and efficient handling of concurrent requests.
2. **SQLite with SQLAlchemy**: Simple, lightweight storage solution for local deployment.
3. **JSON Storage**: Event data is stored in a flexible JSON format to accommodate varying structures.
4. **Indexing Strategy**: Added indexes on frequently queried fields (timestamp, agent_id, event_type).

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 