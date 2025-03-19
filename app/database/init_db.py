import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from app.models.base import Base

# Get DB path from environment or use default
DB_PATH = os.environ.get("CYLESTIO_DB_PATH", "./data/cylestio.db")
DB_DIR = os.path.dirname(DB_PATH)

# Create data directory if it doesn't exist
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

# Create SQLite async engine
SQLALCHEMY_DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL, 
    echo=True,
    connect_args={"check_same_thread": False},  # Needed for SQLite
    future=True
)

# Create async session factory
async_session = sessionmaker(
    engine, 
    class_=AsyncSession,
    expire_on_commit=False,
)

async def init_db():
    """Initialize the database by creating all tables."""
    async with engine.begin() as conn:
        # This will drop all tables and recreate them (remove for production)
        # await conn.run_sync(Base.metadata.drop_all)
        
        # This will create tables if they don't exist
        await conn.run_sync(Base.metadata.create_all)
        
    print("Database tables created successfully.")

async def get_session() -> AsyncSession:
    """Get a database session."""
    async with async_session() as session:
        yield session 