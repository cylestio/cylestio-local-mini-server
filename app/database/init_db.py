import os
import asyncio
import platform
import sys
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from app.models.base import Base

# Get project root directory
def get_project_root():
    """Get the absolute path to the project root directory."""
    return Path(__file__).parent.parent.parent.absolute()

# Get production database path based on OS
def get_production_db_path():
    """Get the production database path based on OS."""
    home = Path.home()
    
    if platform.system() == "Linux":
        db_dir = home / ".config" / "cylestio-monitor"
    elif platform.system() == "Darwin":  # macOS
        db_dir = home / "Library" / "Application Support" / "cylestio-monitor"
    elif platform.system() == "Windows":
        db_dir = home / "AppData" / "Local" / "cylestio" / "cylestio-monitor"
    else:
        db_dir = Path("./data")
    
    # Ensure directory exists
    db_dir.mkdir(parents=True, exist_ok=True)
    return str(db_dir / "cylestio.db")

# Determine if we're in test mode
IS_TEST = "CYLESTIO_TEST_MODE" in os.environ or "pytest" in sys.modules

# Determine the test database type: in-memory or file-based
TEST_DB_TYPE = os.environ.get("CYLESTIO_TEST_DB_TYPE", "file").lower()

# Get DB path from environment or use default
if "CYLESTIO_DB_PATH" in os.environ:
    # If explicitly set, use that path
    DB_PATH = os.environ.get("CYLESTIO_DB_PATH")
elif IS_TEST:
    if TEST_DB_TYPE == "memory":
        # Use in-memory database for unit tests
        DB_PATH = ":memory:"
    else:
        # Use file-based database for integration tests
        # Use absolute path to ensure consistency
        DB_PATH = os.path.join(get_project_root(), "data/test_cylestio.db")
else:
    # Use production database path
    DB_PATH = get_production_db_path()

# Create SQLAlchemy URL
if DB_PATH == ":memory:":
    SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
else:
    # For file-based databases, ensure directory exists
    DB_DIR = os.path.dirname(DB_PATH)
    os.makedirs(DB_DIR, exist_ok=True)
    
    # For relative paths, make them absolute using project root
    if not os.path.isabs(DB_PATH):
        DB_PATH = os.path.join(get_project_root(), DB_PATH)
        
    # Update environment to use absolute path
    os.environ["CYLESTIO_DB_PATH"] = DB_PATH
    
    # Create database URL with absolute path
    SQLALCHEMY_DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

print(f"Using database at: {DB_PATH}")

# Create SQLite async engine
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL, 
    echo=IS_TEST,  # Echo SQL only in test mode
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
        # In test mode, we might want to drop and recreate tables
        if IS_TEST and os.environ.get("CYLESTIO_RESET_TEST_DB", "false").lower() == "true":
            await conn.run_sync(Base.metadata.drop_all)
            print("Test database tables dropped.")
        
        # This will create tables if they don't exist
        await conn.run_sync(Base.metadata.create_all)
        
    print(f"Database tables created successfully at {DB_PATH}")

async def get_session() -> AsyncSession:
    """Get a database session."""
    async with async_session() as session:
        yield session 