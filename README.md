# Cylestio Local Mini Server

A lightweight telemetry processing server for AI agents that provides a modular API for metrics and analytics.

## Overview

Cylestio Local Mini Server is designed to collect, process, and provide access to telemetry data from AI agents. It features a RESTful API that follows a "one endpoint per metric" approach for maximum flexibility and clarity. The server stores telemetry data locally and provides various endpoints for querying metrics related to performance, security, token usage, and system usage.

## Features

- **Modular API Design**: Each metric has its own dedicated endpoint for clarity and specificity
- **Comprehensive Metrics**: Endpoints for performance, security, token usage, and system usage
- **Flexible Filtering**: Filter metrics by time range, agent ID, session ID, and more
- **Local Data Storage**: Data is stored locally in a SQLite database
- **Asynchronous Processing**: Built with FastAPI and async/await for optimal performance
- **Detailed Documentation**: Complete API documentation with examples

## Installation

For detailed installation instructions, see [INSTALLATION.md](INSTALLATION.md).

Quick start:

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

## Usage

### Starting the Server

Start the server with the following command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The server will start on port 8000 by default. You can specify a different port:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 9999
```

### Accessing the API

The API is available at:

```
http://localhost:{PORT}/api/v1/
```

## API Documentation

The API is divided into several modules for different types of metrics:

- **Performance Metrics**: Response time and latency measurements
- **Token Usage Metrics**: Token consumption and cost metrics
- **Security Metrics**: Security alerts and risk assessments
- **Usage Metrics**: Agent and system usage statistics

For detailed API documentation, see [API_DOCUMENTATION.md](API_DOCUMENTATION.md).

### Testing the API

You can test all available endpoints using the included test script:

```bash
python app/test_api.py --url http://localhost:9999 --output results.json
```

## Database

The server uses a SQLite database located at:

- macOS: `~/Library/Application Support/cylestio-monitor/cylestio.db`
- Linux: `~/.config/cylestio-monitor/cylestio.db`
- Windows: `%LOCALAPPDATA%\cylestio\cylestio-monitor\cylestio.db`

## Architecture

The server is built with a modular architecture:

- `app/main.py`: Server startup and configuration
- `app/api/`: API endpoint definitions
- `app/business_logic/`: Core calculation logic for metrics
- `app/database/`: Database models and connection management
- `app/models/`: Data models for the application

## Testing

Run the tests with pytest:

```bash
python -m pytest tests/
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Uses [SQLAlchemy](https://www.sqlalchemy.org/) for database operations
- Documentation created with [MkDocs](https://www.mkdocs.org/) 