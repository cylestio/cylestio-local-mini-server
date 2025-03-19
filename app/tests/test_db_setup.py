import asyncio
import json
import sys
import os
import datetime
from pathlib import Path

# Add parent directory to path for relative imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.database.init_db import create_tables, engine, async_session
from app.models.agent import Agent
from app.models.event import Event
from app.models.session import Session
from app.routers.event_create import create_event

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
    
    print("Sample data loading complete.")

async def test_queries():
    """Run test queries to verify the database setup."""
    
    print("Running test queries...")
    
    async with async_session() as session:
        # Count agents
        from sqlalchemy import func, select
        result = await session.execute(select(func.count(Agent.id)))
        agent_count = result.scalar()
        print(f"Total agents: {agent_count}")
        
        # List agents
        result = await session.execute(select(Agent))
        agents = result.scalars().all()
        for agent in agents:
            print(f"Agent: {agent.agent_id}, Last seen: {agent.last_seen}")
        
        # Count events
        result = await session.execute(select(func.count(Event.id)))
        event_count = result.scalar()
        print(f"Total events: {event_count}")
        
        # Count events by type
        result = await session.execute(
            select(Event.event_type, func.count(Event.id))
            .group_by(Event.event_type)
        )
        print("Events by type:")
        for event_type, count in result:
            print(f"  {event_type}: {count}")
        
        # Count events by channel
        result = await session.execute(
            select(Event.channel, func.count(Event.id))
            .group_by(Event.channel)
        )
        print("Events by channel:")
        for channel, count in result:
            print(f"  {channel}: {count}")

async def main():
    """Main test function."""
    
    # Create tables
    print("Creating database tables...")
    await create_tables()
    
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
    await test_queries()

if __name__ == "__main__":
    asyncio.run(main()) 