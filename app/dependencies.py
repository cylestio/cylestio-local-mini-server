"""
Dependencies for the Cylestio Mini-Local Server.

This module provides FastAPI dependencies for the Cylestio Mini-Local Server.
"""

from typing import Generator, AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
import os

# Get DB path from environment or use default
DB_PATH = os.environ.get("CYLESTIO_DB_PATH", "./data/cylestio.db")

# Create SQLite engine for sync operations
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}  # Needed for SQLite
)

# Create async SQLite engine
ASYNC_SQLALCHEMY_DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"
async_engine = create_async_engine(
    ASYNC_SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},  # Needed for SQLite
)

# Create session factories
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=async_engine, 
    class_=AsyncSession,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """
    Get a database session.
    
    This is a FastAPI dependency for non-async database operations.
    It creates a new database session and closes it after use.
    
    Example:
        ```python
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
        ```
    
    Returns:
        A SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get an async database session.
    
    This is a FastAPI dependency for async database operations.
    It creates a new async database session and closes it after use.
    
    Example:
        ```python
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_session)):
            result = await db.execute(select(Item))
            return result.scalars().all()
        ```
    
    Returns:
        An async SQLAlchemy database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close() 