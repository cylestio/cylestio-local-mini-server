import asyncio
import json
import sys
import os
import datetime
from pathlib import Path
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.pool import NullPool
from app.database.init_db import init_db, engine, async_session

# Add parent directory to path for relative imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.models.agent import Agent
from app.models.event import Event
from app.models.session import Session
from app.routers.event_create import create_event

@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Create a database session for testing."""
    await init_db()
    async with async_session() as session:
        yield session
        await session.close()
    await engine.dispose()

async def load_sample_data(sample_file_path):
    """Load sample data from a JSON file."""
    if not os.path.exists(sample_file_path):
        print(f"Sample file {sample_file_path} not found.")
        return
    
    print(f"Loading sample data from {sample_file_path}...")
    
    # Read the JSON file
    with open(sample_file_path, "r") as f:
        lines = f.readlines()
    
    # Process each line as a separate JSON object
    async with async_session() as session:
        try:
            for i, line in enumerate(lines):
                try:
                    event_data = json.loads(line.strip())
                    
                    # Create event with the create_event function
                    await create_event(event_data, session)
                    
                    if (i + 1) % 10 == 0:
                        print(f"Processed {i + 1} records...")
                    
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON on line {i + 1}: {e}")
                except Exception as e:
                    print(f"Error processing event on line {i + 1}: {e}")
        finally:
            await session.close()
    
    print("Sample data loading complete.")

@pytest.mark.asyncio
async def test_queries(db_session: AsyncSession):
    """Test basic database queries."""
    # Add your test queries here
    pass

async def main():
    """Main test function."""
    # Create tables
    print("Creating database tables...")
    await init_db()
    
    # Load sample data from input_json_records_examples
    base_dir = Path(__file__).parent.parent.parent
    sample_files_dir = base_dir / "input_json_records_examples"
    
    if os.path.exists(sample_files_dir):
        for sample_file in os.listdir(sample_files_dir):
            if sample_file.endswith(".json"):
                await load_sample_data(sample_files_dir / sample_file)
    else:
        print(f"Sample files directory {sample_files_dir} not found.")
    
    # Run test queries
    await test_queries(None)  # Note: This is just for manual testing

if __name__ == "__main__":
    asyncio.run(main()) 