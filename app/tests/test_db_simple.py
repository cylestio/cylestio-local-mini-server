"""
Simple test to demonstrate database configuration.

This file tests the basic functionality of our database configuration:
1. Configure the database through environment variables
2. Verify the configuration is correctly applied
3. Access the database through SQLAlchemy
"""

import os
import sys
import pytest
import asyncio
import sqlite3
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Ensure we can import from the correct path
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Import our configuration utilities
from app.tests.test_config import setup_memory_db, setup_file_db, get_test_db_path

# Ensure data directory exists
data_dir = ROOT_DIR / "data"
data_dir.mkdir(exist_ok=True)

# Set up environment for in-memory testing
setup_memory_db()

# Create engine and session for in-memory database
engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    echo=False,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    engine, 
    expire_on_commit=False, 
    class_=AsyncSession,
)

@pytest.mark.asyncio
async def test_in_memory_db_basic():
    """Test basic in-memory database operations."""
    # Get the configured database path
    db_path = get_test_db_path()
    
    # Verify we're using in-memory database
    assert db_path == ":memory:", "Should be using an in-memory database"
    
    # Create a test table
    async with engine.begin() as conn:
        await conn.execute(text("CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY, value TEXT)"))
    
    # Insert data
    async with SessionLocal() as session:
        await session.execute(text("INSERT INTO test_table (id, value) VALUES (1, 'test value')"))
        await session.commit()
    
    # Query data
    async with SessionLocal() as session:
        result = await session.execute(text("SELECT value FROM test_table WHERE id = 1"))
        value = result.scalar()
    
    # Verify data was inserted and retrieved correctly
    assert value == "test value", "Database operations should work correctly"
    
    print("In-memory database basic test passed - operations work correctly.")

# Now set up environment for file-based testing
@pytest.mark.asyncio
async def test_file_based_db_basic():
    """Test basic file-based database operations."""
    # Set up file-based database with absolute path
    test_db_path = str(ROOT_DIR / "data" / "simple_test.db")
    
    # Create an empty SQLite database file
    con = sqlite3.connect(test_db_path)
    con.close()
    
    # Verify the file was created
    assert os.path.exists(test_db_path), f"Database file {test_db_path} should exist"
    
    # Configure our environment
    db_path = setup_file_db(db_path=test_db_path)
    
    # Verify paths match
    assert db_path == test_db_path, "Database paths should match"
    
    # Create engine and session for file-based database
    file_engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    
    FileSessionLocal = sessionmaker(
        file_engine, 
        expire_on_commit=False, 
        class_=AsyncSession,
    )
    
    # Create a test table
    async with file_engine.begin() as conn:
        await conn.execute(text("CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY, value TEXT)"))
    
    # Insert data
    async with FileSessionLocal() as session:
        await session.execute(text("INSERT INTO test_table (id, value) VALUES (2, 'file-based value')"))
        await session.commit()
    
    # Query data
    async with FileSessionLocal() as session:
        result = await session.execute(text("SELECT value FROM test_table WHERE id = 2"))
        value = result.scalar()
    
    # Verify data was inserted and retrieved correctly
    assert value == "file-based value", "Database operations should work correctly"
    
    print("File-based database test passed - operations work correctly.")
    print(f"Database file preserved at: {os.path.abspath(db_path)}")
    
    # Verify we can open the SQLite file directly
    con = sqlite3.connect(db_path)
    cursor = con.cursor()
    cursor.execute("SELECT value FROM test_table WHERE id = 2")
    direct_value = cursor.fetchone()[0]
    con.close()
    
    assert direct_value == "file-based value", "Direct database access should work"
    print("Direct SQLite access to file verified successfully")

if __name__ == "__main__":
    # Run this specific test file with pytest directly
    pytest.main(["-xvs", __file__]) 