"""
Database helper functions for testing.

This module provides utilities to create test database sessions and
mock database functionality for unit tests.
"""

import asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Callable, AsyncGenerator, Any, Dict, List, Optional, Type, Union, Tuple

class MockQuery:
    """Mock implementation of SQLAlchemy Query object."""
    
    def __init__(self, model_class, results=None):
        self.model_class = model_class
        self.results = results or []
        self.filters = []
    
    def filter(self, *args):
        """Add a filter to the query."""
        self.filters.append(args)
        return self
    
    def filter_by(self, **kwargs):
        """Add a filter_by to the query."""
        self.filters.append(kwargs)
        return self
    
    def first(self):
        """Return the first result or None."""
        if self.results:
            return self.results[0]
        return None
    
    def all(self):
        """Return all results."""
        return self.results
    
    def count(self):
        """Return the count of results."""
        return len(self.results)


class MockDBSession:
    """Mock implementation of a SQLAlchemy database session."""
    
    def __init__(self, query_results=None):
        self.query_results = query_results or {}
        self.added_objects = []
        self.deleted_objects = []
        self.commit_count = 0
        self.rollback_count = 0
        self.query_count = 0
    
    def add(self, obj):
        """Add an object to the session."""
        self.added_objects.append(obj)
    
    def delete(self, obj):
        """Delete an object from the session."""
        self.deleted_objects.append(obj)
    
    def commit(self):
        """Commit the session."""
        self.commit_count += 1
    
    def rollback(self):
        """Rollback the session."""
        self.rollback_count += 1
    
    def query(self, model_class):
        """Query for objects of the given model class."""
        self.query_count += 1
        results = self.query_results.get(model_class, [])
        return MockQuery(model_class, results)
    
    def close(self):
        """Close the session."""
        pass
    
    async def acommit(self):
        """Async commit the session."""
        self.commit_count += 1
    
    async def aclose(self):
        """Async close the session."""
        pass


def mock_db_session_factory(query_results=None):
    """Create a mock database session with predefined query results."""
    return MockDBSession(query_results)


def get_sync_test_db():
    """Get a synchronous SQLite test database session."""
    # This would normally create a real in-memory SQLite database
    # For testing, we just return a mock session
    session = MockDBSession()
    try:
        yield session
    finally:
        session.close()


async def get_async_test_db():
    """Get an asynchronous SQLite test database session."""
    # This would normally create a real async in-memory SQLite database
    # For testing, we just return a mock session
    session = MockDBSession()
    try:
        yield session
    finally:
        await session.aclose() 