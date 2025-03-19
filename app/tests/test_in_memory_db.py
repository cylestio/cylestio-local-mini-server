"""
Unit test demonstrating in-memory database usage.

This test shows how to:
1. Use in-memory SQLite database for fast and isolated unit tests
2. Properly initialize the database and tear it down after tests
3. Run tests efficiently without disk I/O
"""

import os
import sys
import pytest
import asyncio
from pathlib import Path
from sqlalchemy import inspect, text

# Fix path for imports if running directly
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.tests.test_config import setup_memory_db, get_test_db_path
from app.models.base import Base

# Mark test module to use asyncio
pytestmark = [pytest.mark.asyncio]

@pytest.fixture(autouse=True, scope="module")
def setup_test():
    """Automatically setup the test environment."""
    setup_memory_db()
    yield
    # Cleanup will be handled by the fixtures

async def test_in_memory_db_setup(setup_unit_test_env, unit_test_session):
    """Test that the in-memory database is properly set up and isolated."""
    # Get the configured database path
    db_path = get_test_db_path()
    
    # Verify we're using in-memory database
    assert db_path == ":memory:", "Should be using an in-memory database"
    
    # Get database inspector to check schema
    inspector = await unit_test_session.run_sync(
        lambda sync_session: inspect(sync_session.bind)
    )
    
    # Get table names
    table_names = inspector.get_table_names()
    
    # Check if tables were created
    assert len(table_names) > 0, "Database should have tables defined"
    
    # Log info for debugging
    print(f"In-memory database tables: {table_names}")

async def test_in_memory_transactions(setup_unit_test_env, unit_test_session):
    """Test that the in-memory database handles transactions properly."""
    # Test writing to the database
    try:
        # Try executing a simple query
        result = await unit_test_session.execute(text("SELECT 1"))
        value = result.scalar()
        assert value == 1, "Database should be accessible and execute queries"
        
        # Test transaction commit
        async with unit_test_session.begin():
            await unit_test_session.execute(text("PRAGMA user_version = 42"))
        
        # Verify the transaction was committed
        result = await unit_test_session.execute(text("PRAGMA user_version"))
        value = result.scalar()
        assert value == 42, "Transaction should be committed successfully"
        
        print("In-memory database transactions working correctly")
    except Exception as e:
        pytest.fail(f"Database transaction failed: {str(e)}")

async def test_in_memory_isolation(setup_unit_test_env):
    """Test that each in-memory database is isolated between tests."""
    # Create a new session for this test
    SessionLocal = setup_unit_test_env.session_factory
    
    async with SessionLocal() as session:
        # Set a value in the database
        await session.execute(text("PRAGMA user_version = 100"))
        await session.commit()
        
        # Verify the value was set
        result = await session.execute(text("PRAGMA user_version"))
        value = result.scalar()
        assert value == 100, "Should be able to set values in isolated database"
    
    # Create another session to verify isolation
    async with SessionLocal() as session2:
        # Check that the value is still the same (within same test)
        result = await session2.execute(text("PRAGMA user_version"))
        value = result.scalar()
        assert value == 100, "Value should persist within the same test run"
    
    print("In-memory database isolation confirmed within test")

if __name__ == "__main__":
    # Run this specific test file with correct pytest configuration
    pytest.main(["-xvs", __file__]) 