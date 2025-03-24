#!/bin/bash
# Database initialization and migration script for Cylestio Monitor

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project root directory
cd "$PROJECT_ROOT" || exit 1

# Check if database path is set in environment
if [ -z "$CYLESTIO_DB_PATH" ]; then
    DEFAULT_DB_PATH="$PROJECT_ROOT/data/cylestio.db"
    echo "Using default database path: $DEFAULT_DB_PATH"
    export CYLESTIO_DB_PATH="$DEFAULT_DB_PATH"
else
    echo "Using database path from environment: $CYLESTIO_DB_PATH"
fi

# Make sure directory exists
mkdir -p "$(dirname "$CYLESTIO_DB_PATH")"

# Run the migration script
echo "Running database migrations..."
python "$SCRIPT_DIR/migrate_db.py"

# Check if migrations were successful
if [ $? -eq 0 ]; then
    echo "Database initialization and migrations completed successfully"
else
    echo "Error: Database initialization or migrations failed"
    exit 1
fi 