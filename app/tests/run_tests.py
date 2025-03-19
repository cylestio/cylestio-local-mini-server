#!/usr/bin/env python
"""
Test runner script for Cylestio mini-local server.

This script provides a simple way to run tests with different database configurations:
- Unit tests with in-memory database
- Integration tests with file-based database
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# Get the project root directory
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.tests.test_config import (
    setup_memory_db, 
    setup_file_db, 
    reset_test_environment
)

def setup_environment(test_type):
    """Set up the environment for the given test type."""
    reset_test_environment()
    
    if test_type == "unit":
        # Setup in-memory database for unit tests
        os.environ["CYLESTIO_TEST_DB_TYPE"] = "memory"
        os.environ["CYLESTIO_TEST_MODE"] = "true"
        print("Using in-memory database for unit tests")
    elif test_type == "integration":
        # Setup file-based database for integration tests
        os.environ["CYLESTIO_TEST_DB_TYPE"] = "file"
        os.environ["CYLESTIO_TEST_MODE"] = "true"
        os.environ["CYLESTIO_PRESERVE_TEST_DB"] = "true"
        print("Using file-based database for integration tests")
    else:
        # Setup both test types but use file-based for safety
        os.environ["CYLESTIO_TEST_DB_TYPE"] = "file"
        os.environ["CYLESTIO_TEST_MODE"] = "true"
        os.environ["CYLESTIO_PRESERVE_TEST_DB"] = "true"
        print("Using file-based database for all tests")

def run_unit_tests(args):
    """Run unit tests with in-memory database."""
    setup_environment("unit")
    
    # Build pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add verbosity
    if args.verbose:
        cmd.append("-v")
    
    # Ensure we have the right working directory
    os.chdir(ROOT_DIR)
    
    # Add test paths or use default
    if args.test_paths:
        cmd.extend(args.test_paths)
    else:
        # Default to non-integration tests
        cmd.append("app/tests/test_in_memory_db.py")
        cmd.append("app/tests/test_models.py")
        cmd.append("app/tests/test_api_v1.py")
    
    # Add markers if specified
    if args.markers:
        marker_arg = "-m " + " or ".join(args.markers)
        cmd.append(marker_arg)
    
    # Execute the pytest command
    print(f"Running unit tests with command: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode

def run_integration_tests(args):
    """Run integration tests with file-based database."""
    setup_environment("integration")
    
    # Build pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add verbosity
    if args.verbose:
        cmd.append("-v")
    
    # Ensure we have the right working directory
    os.chdir(ROOT_DIR)
    
    # Add test paths or use default
    if args.test_paths:
        cmd.extend(args.test_paths)
    else:
        # Default to integration test directory
        cmd.append("app/tests/integration/")
    
    # Add markers if specified
    if args.markers:
        marker_arg = "-m " + " or ".join(args.markers)
        cmd.append(marker_arg)
    
    # Execute the pytest command
    print(f"Running integration tests with command: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    
    # Print database location for manual inspection
    if os.environ.get("CYLESTIO_DB_PATH"):
        db_path = os.environ.get("CYLESTIO_DB_PATH")
    else:
        db_path = "./data/test_cylestio.db"
    
    print("\n==============================================")
    print(f"Database file preserved at: {os.path.abspath(db_path)}")
    print("You can inspect it with: sqlite3 or DB Browser for SQLite")
    print("==============================================\n")
    
    return result.returncode

def run_all_tests(args):
    """Run both unit and integration tests."""
    # Run unit tests first
    unit_result = run_unit_tests(args)
    
    # Run integration tests second
    integration_result = run_integration_tests(args)
    
    # Return non-zero if either test suite failed
    return max(unit_result, integration_result)

def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(description="Run Cylestio tests with different database configurations")
    
    parser.add_argument("--type", choices=["unit", "integration", "all"], default="all",
                       help="Type of tests to run (unit=in-memory, integration=file-based, all=both)")
    
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Run tests in verbose mode")
    
    parser.add_argument("--markers", "-m", nargs="+",
                       help="Only run tests with specified markers")
    
    parser.add_argument("test_paths", nargs="*",
                       help="Paths to test files or directories")
    
    args = parser.parse_args()
    
    # Run the specified test type
    if args.type == "unit":
        return run_unit_tests(args)
    elif args.type == "integration":
        return run_integration_tests(args)
    else:
        return run_all_tests(args)

if __name__ == "__main__":
    sys.exit(main()) 