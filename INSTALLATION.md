# Cylestio Mini-Local Server: Installation Guide

This guide provides instructions for installing and setting up the Cylestio Mini-Local Server on your system.

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Virtual environment (recommended)

## Installation Steps

### 1. Clone or Download the Repository

```bash
git clone https://github.com/cylestio/cylestio-local-mini-server.git
cd cylestio-local-mini-server
```

### 2. Create and Activate a Virtual Environment (Recommended)

#### Linux/macOS:
```bash
python -m venv venv
source venv/bin/activate
```

#### Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Verify Installation

Run the tests to ensure everything is working correctly:

```bash
python -m pytest tests/
```

## Running the Server

To start the Cylestio Mini-Local Server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

By default, the server will be accessible at `http://localhost:8000`.

## Configuration

The server can be configured using environment variables:

- `CYLESTIO_DB_PATH`: Path to the SQLite database file (default: platform-specific location)
- `CYLESTIO_TEST_MODE`: Set to "true" to enable test mode
- `CYLESTIO_RESET_TEST_DB`: Set to "true" to reset the database during testing

## Troubleshooting

### Common Issues

1. **Installation Errors**:
   - Ensure you're using Python 3.8 or higher: `python --version`
   - Make sure pip is up to date: `pip install --upgrade pip`

2. **Database Errors**:
   - Check file permissions for the database directory
   - Verify the database path is correctly set

3. **Test Failures**:
   - Ensure all dependencies are installed correctly
   - Check if the database can be accessed by the tests 