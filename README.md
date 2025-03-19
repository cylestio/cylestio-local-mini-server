# Cylestio Mini-Local Server

A lightweight server for collecting, storing, and querying Cylestio monitoring data.

## 📋 Contents

- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Setup and Installation](#setup-and-installation)
- [Configuration](#configuration)
- [Running the Server](#running-the-server)
- [API Endpoints](#api-endpoints)
- [Database Schema](#database-schema)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## 🚀 Quick Start

The fastest way to get Cylestio running is with the following commands:

```bash
# Clone the repository
git clone https://github.com/cylestio/cylestio-local-mini-server.git
cd cylestio-local-mini-server

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn app.main:app --reload
```

The server will be available at http://localhost:8000 with API documentation at http://localhost:8000/docs.

## 🏗️ Architecture

- **Python Monitoring SDK** sends telemetry via REST API to Mini-Local Server
- **Mini-Local Server** processes and stores data in SQLite database
- **Dashboard** queries the Mini-Local Server via REST API

## 📁 Project Structure

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
├── run_tests.sh        - Test runner script
└── requirements.txt    - Project dependencies
```

## ⚙️ Setup and Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git (for cloning the repository)

### Installation Steps

1. **Clone the repository**

   ```bash
   git clone https://github.com/cylestio/cylestio-local-mini-server.git
   cd cylestio-local-mini-server
   ```

2. **Create and activate a virtual environment**

   **Linux/macOS:**
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

   **Windows:**
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Verify installation**

   ```bash
   python -c "import fastapi, uvicorn, sqlalchemy, aiosqlite"
   ```

## ⚙️ Configuration

### Database Location

The server automatically configures the database location based on your operating system:

- **Linux**: `~/.config/cylestio-monitor/cylestio.db`
- **macOS**: `~/Library/Application Support/cylestio-monitor/cylestio.db`
- **Windows**: `C:\Users\<username>\AppData\Local\cylestio\cylestio-monitor\cylestio.db`

For testing purposes, a separate database is created at `./data/test_cylestio.db`.

### Override Database Location

You can override the database location by setting the `CYLESTIO_DB_PATH` environment variable:

**Linux/macOS:**
```bash
export CYLESTIO_DB_PATH=/path/to/custom/database.db
```

**Windows:**
```cmd
set CYLESTIO_DB_PATH=C:\path\to\custom\database.db
```

### Other Environment Variables

- `CYLESTIO_TEST_MODE`: Set to "true" to use test configurations
- `CYLESTIO_RESET_TEST_DB`: Set to "true" to drop and recreate database tables during test
- `CYLESTIO_PRESERVE_TEST_DB`: Set to "true" to keep the test database after tests complete

## 🚀 Running the Server

### Development Mode

Start the development server with automatic reloading:

```bash
uvicorn app.main:app --reload
```

The server will be available at http://localhost:8000.

### Production Mode

For production deployment, run:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### API Documentation

Built-in API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🔌 API Endpoints

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

## 🗄️ Database Schema

The system uses SQLAlchemy ORM with SQLite for data storage. Key tables:

- **agents** - Information about monitored agents
- **events** - Telemetry events from agents
- **sessions** - Conversation sessions and interactions

## 🧪 Testing

### Using the Test Runner Script

The `run_tests.sh` script provides convenient options for running tests:

```bash
# Show test options
./run_tests.sh

# Run all tests
./run_tests.sh all

# Run unit tests only (in-memory database)
./run_tests.sh unit

# Run integration tests only (file-based database)
./run_tests.sh integration

# Run tests that use preserved database
./run_tests.sh preserved

# Clean up test database files
./run_tests.sh clean

# Run tests in verbose mode
./run_tests.sh unit -v
```

### Manual Test Execution

If you prefer to run tests directly with pytest:

```bash
# Run all tests
pytest app/tests

# Run unit tests
CYLESTIO_TEST_DB_TYPE=memory pytest app/tests -k "not integration"

# Run integration tests
CYLESTIO_TEST_DB_TYPE=file pytest app/tests/integration
```

## 🔧 Troubleshooting

### Common Issues

1. **Database not found or permission errors**
   - Check that the database directory exists and has proper write permissions
   - Verify the `CYLESTIO_DB_PATH` environment variable if you're overriding the default location
   - Solution: `mkdir -p ~/.config/cylestio-monitor` (Linux) or equivalent for your OS

2. **Port already in use**
   - Error: `OSError: [Errno 48] Address already in use`
   - Solution: Change the port with `uvicorn app.main:app --port 8001`

3. **Module not found errors**
   - Ensure you've activated the virtual environment
   - Verify all dependencies are installed: `pip install -r requirements.txt`

4. **Test failures**
   - Clean the test database: `./run_tests.sh clean`
   - Reset your environment variables
   - Check for specific errors in test output

### Viewing Logs

For detailed operation logs, run the server with increased verbosity:

```bash
uvicorn app.main:app --log-level debug
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

For more detailed deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md). 