#!/bin/bash

# Default directory for test databases
DATA_DIR="./data"
TEST_DB_PATH="$DATA_DIR/test_cylestio.db"

# Create data directory if it doesn't exist
mkdir -p "$DATA_DIR"

# Function to display help
show_help() {
  echo "Cylestio Test Runner Script"
  echo ""
  echo "Usage: ./run_tests.sh [command] [options]"
  echo ""
  echo "Commands:"
  echo "  all            Run all tests"
  echo "  unit           Run only unit tests (in-memory database)"
  echo "  integration    Run only integration tests (file-based database)"
  echo "  preserved      Run tests that use preserved database"
  echo "  clean          Remove test database files"
  echo ""
  echo "Options:"
  echo "  -v, --verbose  Run tests in verbose mode"
  echo "  -h, --help     Show this help message"
  echo ""
  echo "Examples:"
  echo "  ./run_tests.sh unit -v         Run unit tests in verbose mode"
  echo "  ./run_tests.sh integration     Run integration tests"
  echo "  ./run_tests.sh preserved       Run tests with preserved database"
  echo "  ./run_tests.sh clean           Clean up test database files"
}

# Function to clean up test database files
cleanup_test_db() {
  echo "Cleaning up test database files..."
  if [ -f "$TEST_DB_PATH" ]; then
    rm "$TEST_DB_PATH"
    echo "Removed $TEST_DB_PATH"
  else
    echo "No test database found at $TEST_DB_PATH"
  fi
  
  # Remove any other test databases in data directory
  find "$DATA_DIR" -name "*.db" -type f -delete

  echo "Cleanup complete"
}

# Parse command line arguments
if [ $# -eq 0 ]; then
  show_help
  exit 0
fi

command=$1
shift

# Default options
verbose=""

# Parse options
while [ "$#" -gt 0 ]; do
  case "$1" in
    -v|--verbose)
      verbose="-v"
      shift
      ;;
    -h|--help)
      show_help
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      show_help
      exit 1
      ;;
  esac
done

# Execute the appropriate command
case "$command" in
  all)
    echo "Running all tests..."
    python -m pytest app/tests $verbose
    ;;
    
  unit)
    echo "Running unit tests with in-memory database..."
    export CYLESTIO_TEST_DB_TYPE="memory"
    python -m pytest app/tests -k "not integration" $verbose
    ;;
    
  integration)
    echo "Running integration tests with file-based database..."
    export CYLESTIO_TEST_DB_TYPE="file"
    export CYLESTIO_DB_PATH="$TEST_DB_PATH"
    python -m pytest app/tests/integration $verbose
    ;;
    
  preserved)
    echo "Running tests with preserved database..."
    export CYLESTIO_TEST_DB_TYPE="file"
    export CYLESTIO_DB_PATH="$TEST_DB_PATH"
    export CYLESTIO_PRESERVE_TEST_DB="true"
    echo "Test database will be preserved at $TEST_DB_PATH"
    python -m pytest app/tests/integration/test_db_preserved.py app/tests/integration/test_telemetry_integration.py $verbose
    echo "Tests completed. Database preserved at $TEST_DB_PATH"
    echo "Use 'sqlite3 $TEST_DB_PATH' to inspect the database."
    ;;
    
  clean)
    cleanup_test_db
    ;;
    
  *)
    echo "Unknown command: $command"
    show_help
    exit 1
    ;;
esac

exit 0 