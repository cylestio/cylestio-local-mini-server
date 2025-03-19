# Cylestio Mini-Local Server: Deployment Guide

This guide provides detailed instructions for deploying the Cylestio Mini-Local Server on different operating systems.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [Linux](#linux)
  - [macOS](#macos)
  - [Windows](#windows)
- [Configuration](#configuration)
- [Running the Server](#running-the-server)
- [Database Setup](#database-setup)
- [Testing](#testing)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Troubleshooting](#troubleshooting)

## Prerequisites

Before installing the Cylestio Mini-Local Server, ensure you have the following prerequisites:

- Python 3.8+ installed
- pip (Python package manager)
- Git (optional, for cloning the repository)
- Network connectivity for the server to communicate with clients

## Installation

### Linux

1. **Clone or download the repository**

   ```bash
   git clone https://github.com/cylestio/cylestio-local-mini-server.git
   cd cylestio-local-mini-server
   ```

2. **Create and activate a virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install the required dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Verify installation**

   ```bash
   python -c "import fastapi, uvicorn, sqlalchemy, aiosqlite"
   ```

### macOS

1. **Clone or download the repository**

   ```bash
   git clone https://github.com/cylestio/cylestio-local-mini-server.git
   cd cylestio-local-mini-server
   ```

2. **Create and activate a virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install the required dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Verify installation**

   ```bash
   python -c "import fastapi, uvicorn, sqlalchemy, aiosqlite"
   ```

### Windows

1. **Clone or download the repository**

   ```cmd
   git clone https://github.com/cylestio/cylestio-local-mini-server.git
   cd cylestio-local-mini-server
   ```

2. **Create and activate a virtual environment**

   ```cmd
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install the required dependencies**

   ```cmd
   pip install -r requirements.txt
   ```

4. **Verify installation**

   ```cmd
   python -c "import fastapi, uvicorn, sqlalchemy, aiosqlite"
   ```

## Configuration

The Cylestio Mini-Local Server is configured using environment variables:

- `CYLESTIO_DB_PATH`: Path to the SQLite database file. If not set, the default is an OS-specific path:
  - **Linux**: `~/.config/cylestio-monitor/cylestio.db`
  - **macOS**: `~/Library/Application Support/cylestio-monitor/cylestio.db`
  - **Windows**: `C:\Users\<username>\AppData\Local\cylestio\cylestio-monitor\cylestio.db`

- `CYLESTIO_TEST_MODE`: Set to "true" to use test configurations
- `CYLESTIO_RESET_TEST_DB`: Set to "true" to drop and recreate database tables during test

## Running the Server

To run the Cylestio Mini-Local Server:

1. **Activate your virtual environment (if not already active)**

   - Linux/macOS: `source venv/bin/activate`
   - Windows: `venv\Scripts\activate`

2. **Start the server**

   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

   This will start the server on all network interfaces on port 8000.

3. **Verify the server is running**

   Open a web browser and navigate to `http://localhost:8000/` or use cURL:

   ```bash
   curl http://localhost:8000/
   ```

   You should see a response indicating the server is healthy.

### Running as a Service

#### Linux (systemd)

Create a systemd service file at `/etc/systemd/system/cylestio-server.service`:

```ini
[Unit]
Description=Cylestio Mini-Local Server
After=network.target

[Service]
User=<your-username>
WorkingDirectory=/path/to/cylestio-local-mini-server
ExecStart=/path/to/cylestio-local-mini-server/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl enable cylestio-server
sudo systemctl start cylestio-server
```

#### macOS (launchd)

Create a launchd plist file at `~/Library/LaunchAgents/com.cylestio.mini-server.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cylestio.mini-server</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/cylestio-local-mini-server/venv/bin/uvicorn</string>
        <string>app.main:app</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>8000</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>/path/to/cylestio-local-mini-server</string>
    <key>StandardErrorPath</key>
    <string>/tmp/cylestio-server.err</string>
    <key>StandardOutPath</key>
    <string>/tmp/cylestio-server.out</string>
</dict>
</plist>
```

Load and start the service:

```bash
launchctl load ~/Library/LaunchAgents/com.cylestio.mini-server.plist
launchctl start com.cylestio.mini-server
```

#### Windows (Windows Service)

Using NSSM (Non-Sucking Service Manager):

1. Download and install NSSM from https://nssm.cc/
2. Open a Command Prompt as Administrator
3. Set up the service:

```cmd
nssm install CylestioServer
```

This will open a GUI:
- Path: `C:\path\to\cylestio-local-mini-server\venv\Scripts\uvicorn.exe`
- Arguments: `app.main:app --host 0.0.0.0 --port 8000`
- Startup directory: `C:\path\to\cylestio-local-mini-server`

Start the service:

```cmd
nssm start CylestioServer
```

## Database Setup

The Cylestio Mini-Local Server uses SQLite for data storage. The database will be automatically created and initialized when the server starts.

### Production Database Locations

The default production database locations are:

- **Linux**: `~/.config/cylestio-monitor/cylestio.db`
- **macOS**: `~/Library/Application Support/cylestio-monitor/cylestio.db`
- **Windows**: `C:\Users\<username>\AppData\Local\cylestio\cylestio-monitor\cylestio.db`

### Test Database Location

For testing purposes, the database is located at `./data/test_cylestio.db`.

### Manually Specify Database Location

You can manually specify the database location by setting the `CYLESTIO_DB_PATH` environment variable:

- Linux/macOS:
  ```bash
  export CYLESTIO_DB_PATH=/path/to/your/custom/database.db
  ```

- Windows:
  ```cmd
  set CYLESTIO_DB_PATH=C:\path\to\your\custom\database.db
  ```

## Testing

### Running Unit Tests

To run the unit tests:

```bash
pytest app/tests
```

### Running Integration Tests

To run the integration tests:

```bash
# Using test database (default)
python app/tests/integration/run_e2e_integration.py

# Using production database
python app/tests/integration/run_e2e_integration.py --production-db

# Using an already running server
python app/tests/integration/run_e2e_integration.py --no-server
```

## Monitoring and Maintenance

### Monitoring Server Status

To check if the server is running:

```bash
curl http://localhost:8000/
```

### Viewing Logs

- For servers running in the foreground, logs are printed to the console.
- For servers running as a service:
  - Linux: `sudo journalctl -u cylestio-server`
  - macOS: Check `/tmp/cylestio-server.out` and `/tmp/cylestio-server.err`
  - Windows: Use Event Viewer or check the service logs

### Database Backup

To backup the SQLite database:

```bash
# Get the database path
python -c "from app.database.init_db import DB_PATH; print(DB_PATH)"

# Create a backup
cp /path/to/database/cylestio.db /path/to/backup/cylestio-backup-$(date +%Y%m%d).db
```

## Troubleshooting

### Common Issues

1. **Server won't start**
   - Check that the required port (default 8000) is available
   - Verify Python and package dependencies
   - Check if the database file is accessible

2. **Cannot connect to server**
   - Verify the server is running
   - Check firewall settings
   - Make sure you're using the correct URL

3. **Database errors**
   - Check file permissions for the database directory
   - Verify the database path is correctly set

### Getting Help

If you encounter issues that you cannot resolve, please:

1. Check the GitHub repository issues: https://github.com/cylestio/cylestio-local-mini-server/issues
2. Create a new issue with detailed information about your problem

---

For additional information or updates, please refer to the project's GitHub repository. 