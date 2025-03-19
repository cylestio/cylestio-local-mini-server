import pytest
import asyncio
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database.init_db import get_session
from app.models.base import Base

# Use in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test engine
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = sessionmaker(
    test_engine, 
    expire_on_commit=False, 
    class_=AsyncSession
)

# Use pytest's event_loop fixture instead of creating our own
@pytest_asyncio.fixture(scope="function")
async def setup_test_db():
    """Setup the test database for each test."""
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Clean up after each test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def async_session(setup_test_db):
    """Return a session for the test database."""
    async with TestingSessionLocal() as session:
        yield session

@pytest_asyncio.fixture
async def override_get_session():
    """Override the get_session dependency in FastAPI."""
    async def _override_get_session():
        async with TestingSessionLocal() as session:
            yield session
    
    # Override the dependency
    app.dependency_overrides[get_session] = _override_get_session
    
    yield
    
    # Clean up
    app.dependency_overrides.clear()

@pytest.fixture
def test_client(override_get_session):
    """Return a TestClient for testing FastAPI routes."""
    with TestClient(app) as client:
        yield client 