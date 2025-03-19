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
│   ├── api/            - API implementation
│   ├── database/       - Database connection and utilities
│   ├── models/         - SQLAlchemy models
│   ├── routers/        - API route handlers
│   ├── transformers/   - Data transformation utilities
│   └── tests/          - Unit and integration tests
│       └── integration/  - End-to-end integration tests
├── data/               - SQLite database files (created at runtime)
├── resources/          - Sample data and resources
└── Makefile            - Common tasks automation
```

## Quick Start with Make

We provide a Makefile to simplify common tasks. To see all available commands:

```bash
make help
```

Setup your environment, install dependencies, and run the server:

```bash
make setup
make run
```

## Setup and Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/cylestio/cylestio-local-mini-server.git
   cd cylestio-local-mini-server
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Database Configuration

The server automatically configures the database location based on your operating system:

- **Linux**: `~/.config/cylestio-monitor/cylestio.db`
- **macOS**: `~/Library/Application Support/cylestio-monitor/cylestio.db`
- **Windows**: `C:\Users\<username>\AppData\Local\cylestio\cylestio-monitor\cylestio.db`

For testing purposes, a separate database is created at `./data/test_cylestio.db`.

You can override the database location by setting the `CYLESTIO_DB_PATH` environment variable:

```bash
# Linux/macOS
export CYLESTIO_DB_PATH=/path/to/custom/database.db

# Windows
set CYLESTIO_DB_PATH=C:\path\to\custom\database.db
```

## Running the Server

Start the development server:
```bash
uvicorn app.main:app --reload
```

The server will be available at http://localhost:8000.

API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Telemetry Ingestion

- `POST /api/v1/telemetry` - Ingest a single telemetry event
- `POST /api/v1/telemetry/batch` - Ingest a batch of telemetry events

### Agents

- `GET /api/agents` - List all agents
- `GET /api/agents/{agent_id}` - Get detailed information about a specific agent
- `GET /api/agents/{agent_id}/summary` - Get summary statistics for a specific agent

### Events

- `GET /api/events` - List events with filtering options
- `GET /api/events/{agent_id}` - Get events for a specific agent
- `GET /api/events/{agent_id}/{event_type}` - Get events of a specific type for an agent

### Metrics

- `GET /api/metrics/{agent_id}/event_counts` - Get event count metrics for an agent
- `GET /api/metrics/{agent_id}/event_types` - Get event type distribution for an agent
- `GET /api/metrics/{agent_id}/latency` - Get latency metrics for an agent

## Database Schema

The system uses SQLAlchemy ORM with SQLite for data storage. Key tables:

- **agents** - Information about monitored agents
- **events** - Telemetry events from agents
- **sessions** - Conversation sessions and interactions

## Running Tests

Run all tests:
```bash
make test
```

Run unit tests:
```bash
make test-unit
```

Run integration tests:
```bash
make test-integration
```

Or manually:
```bash
# Unit tests
CYLESTIO_TEST_MODE=true pytest app/tests

# Integration tests
python app/tests/integration/run_e2e_integration.py
```

## End-to-End Integration Testing

The integration test suite simulates the complete flow of telemetry data:

1. Starts the server (if not already running)
2. Sends example telemetry records to the API
3. Verifies data storage and transformation
4. Simulates dashboard queries
5. Tests error handling

Run with options:
```bash
# Using test database (default)
python app/tests/integration/run_e2e_integration.py

# Using production database
python app/tests/integration/run_e2e_integration.py --production-db

# Using an already running server
python app/tests/integration/run_e2e_integration.py --no-server
```

## Deployment

For detailed deployment instructions for Linux, macOS, and Windows, see [DEPLOYMENT.md](DEPLOYMENT.md).

## Design Decisions

1. **Async FastAPI**: Used for non-blocking I/O and efficient handling of concurrent requests.
2. **SQLite with SQLAlchemy**: Simple, lightweight storage solution for local deployment.
3. **JSON Storage**: Event data is stored in a flexible JSON format to accommodate varying structures.
4. **Indexing Strategy**: Added indexes on frequently queried fields (timestamp, agent_id, event_type).
5. **OS-Specific Configuration**: Database paths follow OS conventions for application data storage.
6. **Background Processing**: Telemetry ingestion uses FastAPI background tasks for non-blocking operation.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 