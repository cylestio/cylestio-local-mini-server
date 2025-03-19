"""
Dependencies for the Cylestio Mini-Local Server.

This module provides FastAPI dependencies for the Cylestio Mini-Local Server.
"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os

# Get DB path from environment or use default
DB_PATH = os.environ.get("CYLESTIO_DB_PATH", "./data/cylestio.db")

# Create SQLite engine
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}  # Needed for SQLite
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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