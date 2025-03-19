"""
Test configuration utilities to manage test database settings.

This module provides utilities for configuring different test environments:
- Unit tests: Uses in-memory SQLite database
- Integration tests: Uses file-based SQLite database that is preserved for inspection
"""

import os
import sys
import tempfile
from pathlib import Path

# Constants for test database configuration
TEST_DB_TYPE_MEMORY = "memory"
TEST_DB_TYPE_FILE = "file"
TEST_DB_DIR = "./data"
TEST_DB_FILENAME = "test_cylestio.db"
DEFAULT_TEST_DB_PATH = f"{TEST_DB_DIR}/{TEST_DB_FILENAME}"

def get_project_root():
    """Get the absolute path to the project root directory."""
    # The test_config.py file is in app/tests, so go up two directories
    return Path(__file__).parent.parent.parent.absolute()

def setup_memory_db():
    """Configure environment for in-memory database testing (unit tests)."""
    os.environ["CYLESTIO_TEST_MODE"] = "true"
    os.environ["CYLESTIO_TEST_DB_TYPE"] = TEST_DB_TYPE_MEMORY
    
    # Clear any existing DB_PATH to ensure we use the in-memory DB
    if "CYLESTIO_DB_PATH" in os.environ:
        del os.environ["CYLESTIO_DB_PATH"]
    
    print("Test environment configured for in-memory database (unit tests)")
    return ":memory:"

def setup_file_db(db_path=None, preserve_db=True):
    """
    Configure environment for file-based database testing (integration tests).
    
    Args:
        db_path: Optional specific path for the test database
        preserve_db: Whether to preserve the database file after tests
        
    Returns:
        Path to the database file
    """
    os.environ["CYLESTIO_TEST_MODE"] = "true"
    os.environ["CYLESTIO_TEST_DB_TYPE"] = TEST_DB_TYPE_FILE
    
    # Use specified path or default, ensuring it's absolute
    if db_path:
        # Convert to absolute path if it's not already
        if not os.path.isabs(db_path):
            db_path = os.path.join(get_project_root(), db_path)
    else:
        # Use default path, making it absolute
        db_path = os.path.join(get_project_root(), DEFAULT_TEST_DB_PATH)
    
    os.environ["CYLESTIO_DB_PATH"] = db_path
    
    # Control whether we allow reset/deletion of the database
    os.environ["CYLESTIO_PRESERVE_TEST_DB"] = str(preserve_db).lower()
    
    # Ensure data directory exists with proper permissions
    db_dir = Path(os.path.dirname(db_path))
    db_dir.mkdir(parents=True, exist_ok=True, mode=0o755)  # Ensure directory has proper permissions
    
    # Create an empty database file if it doesn't exist to ensure permissions are correct
    if not os.path.exists(db_path) or os.path.getsize(db_path) == 0:
        print(f"Creating new test database file at {db_path}")
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.close()
    
    print(f"Test environment configured for file-based database (integration tests) at {db_path}")
    return db_path

def get_test_db_path():
    """Get the currently configured test database path."""
    if os.environ.get("CYLESTIO_TEST_DB_TYPE") == TEST_DB_TYPE_MEMORY:
        return ":memory:"
    
    db_path = os.environ.get("CYLESTIO_DB_PATH", DEFAULT_TEST_DB_PATH)
    # Ensure path is absolute for consistency
    if not os.path.isabs(db_path) and db_path != ":memory:":
        db_path = os.path.join(get_project_root(), db_path)
    
    return db_path

def should_preserve_db():
    """Check if the test database should be preserved."""
    return os.environ.get("CYLESTIO_PRESERVE_TEST_DB", "true").lower() == "true"

def reset_test_environment():
    """Reset test environment variables to their defaults."""
    for key in ["CYLESTIO_TEST_MODE", "CYLESTIO_TEST_DB_TYPE", 
                "CYLESTIO_DB_PATH", "CYLESTIO_PRESERVE_TEST_DB",
                "CYLESTIO_RESET_TEST_DB"]:
        if key in os.environ:
            del os.environ[key] 