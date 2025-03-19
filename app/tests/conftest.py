import os
import sys
import pytest
import asyncio
import pytest_asyncio
import shutil
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Fix Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.main import app
from app.database.init_db import get_session
from app.models.base import Base
from app.tests.test_config import (
    setup_memory_db, 
    setup_file_db, 
    should_preserve_db, 
    get_test_db_path,
    reset_test_environment,
    get_project_root
)

# Setup fixtures for unit tests using in-memory database
@pytest.fixture(scope="function")
async def setup_unit_test_env():
    """Setup the environment for unit tests with in-memory database."""
    # Configure environment for in-memory database
    db_path = setup_memory_db()
    
    # Create test engine for in-memory database
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        future=True
    )
    
    # Create all tables from Base metadata
    async with test_engine.begin() as conn:
        await conn.run_sync(lambda conn: Base.metadata.create_all(conn))
    
    # Session factory for in-memory tests
    TestingSessionLocal = sessionmaker(
        test_engine, 
        expire_on_commit=False, 
        class_=AsyncSession
    )
    
    # Store engine and session factory in function attributes to access in other fixtures
    setup_unit_test_env.engine = test_engine
    setup_unit_test_env.session_factory = TestingSessionLocal
    
    yield
    
    # Reset environment after test
    reset_test_environment()

# Setup fixtures for integration tests using file-based database
@pytest.fixture(scope="function")
async def setup_integration_test_env():
    """Setup the environment for integration tests with file-based database."""
    # Configure environment for file-based database
    db_path = setup_file_db()
    
    # Ensure the path is absolute
    if not os.path.isabs(db_path) and db_path != ":memory:":
        db_path = os.path.join(get_project_root(), db_path)
        
    # Ensure the database directory exists
    db_dir = os.path.dirname(db_path)
    os.makedirs(db_dir, exist_ok=True)
    
    print(f"Integration test using database at: {db_path}")
    
    # Create test engine for file-based database
    test_engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        echo=False,
        connect_args={"check_same_thread": False},
        future=True
    )
    
    # Create all tables from Base metadata
    async with test_engine.begin() as conn:
        await conn.run_sync(lambda conn: Base.metadata.create_all(conn))
    
    # Session factory for file-based tests
    TestingSessionLocal = sessionmaker(
        test_engine, 
        expire_on_commit=False, 
        class_=AsyncSession
    )
    
    # Store engine and session factory in function attributes
    setup_integration_test_env.engine = test_engine
    setup_integration_test_env.session_factory = TestingSessionLocal
    
    yield
    
    # Only reset environment, don't delete the database file
    reset_test_environment()

# Database setup for unit tests (in-memory)
@pytest_asyncio.fixture(scope="function")
async def setup_unit_test_db(setup_unit_test_env):
    """Setup the in-memory test database for unit tests."""
    engine = setup_unit_test_env.engine
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Clean up after each test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

# Database setup for integration tests (file-based)
@pytest_asyncio.fixture(scope="function")
async def setup_integration_test_db(setup_integration_test_env):
    """Setup the file-based test database for integration tests."""
    engine = setup_integration_test_env.engine
    
    # Create tables
    async with engine.begin() as conn:
        # Only drop tables if we're not preserving the database
        if not should_preserve_db():
            await conn.run_sync(Base.metadata.drop_all)
        
        # Create tables if they don't exist
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # The important difference: don't drop tables if we want to preserve the database
    if not should_preserve_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

# Session fixtures for unit tests
@pytest_asyncio.fixture
async def unit_test_session(setup_unit_test_db, setup_unit_test_env):
    """Return a session for the in-memory unit test database."""
    SessionLocal = setup_unit_test_env.session_factory
    async with SessionLocal() as session:
        yield session

# Session fixtures for integration tests
@pytest_asyncio.fixture
async def integration_test_session(setup_integration_test_db, setup_integration_test_env):
    """Return a session for the file-based integration test database."""
    SessionLocal = setup_integration_test_env.session_factory
    async with SessionLocal() as session:
        yield session
        await session.commit()  # Make sure changes are committed

# Override get_session for unit tests
@pytest_asyncio.fixture
async def override_get_session_unit_test(setup_unit_test_env):
    """Override the get_session dependency for unit tests."""
    SessionLocal = setup_unit_test_env.session_factory
    
    async def _override_get_session():
        async with SessionLocal() as session:
            yield session
    
    # Override the dependency
    app.dependency_overrides[get_session] = _override_get_session
    
    yield
    
    # Clean up
    app.dependency_overrides.clear()

# Override get_session for integration tests
@pytest_asyncio.fixture
async def override_get_session_integration_test(setup_integration_test_env):
    """Override the get_session dependency for integration tests."""
    SessionLocal = setup_integration_test_env.session_factory
    
    async def _override_get_session():
        async with SessionLocal() as session:
            yield session
    
    # Override the dependency
    app.dependency_overrides[get_session] = _override_get_session
    
    yield
    
    # Clean up
    app.dependency_overrides.clear()

# Test client for unit tests
@pytest.fixture
def unit_test_client(override_get_session_unit_test):
    """Return a TestClient for unit testing FastAPI routes."""
    with TestClient(app) as client:
        yield client

# Test client for integration tests
@pytest.fixture
def integration_test_client(override_get_session_integration_test):
    """Return a TestClient for integration testing FastAPI routes."""
    with TestClient(app) as client:
        yield client

# Legacy fixtures for backward compatibility
@pytest_asyncio.fixture(scope="function")
async def setup_test_db():
    """Legacy fixture for backward compatibility."""
    # Configure environment
    db_path = setup_memory_db()
    
    # Create test engine
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        future=True
    )
    
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    # Session factory for backward compatibility
    global TestingSessionLocal
    TestingSessionLocal = sessionmaker(
        test_engine, 
        expire_on_commit=False, 
        class_=AsyncSession
    )
    
    yield
    
    # Clean up after each test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def async_session(setup_test_db):
    """Legacy fixture for backward compatibility."""
    async with TestingSessionLocal() as session:
        yield session

@pytest_asyncio.fixture
async def override_get_session():
    """Legacy fixture for backward compatibility."""
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
    """Legacy fixture for backward compatibility."""
    with TestClient(app) as client:
        yield client 