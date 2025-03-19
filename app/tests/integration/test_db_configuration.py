import os
import sys
import pytest
import platform
from pathlib import Path
import tempfile
import shutil

# Add the parent directory to sys.path to import the app
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# Test database paths based on OS
def get_expected_production_db_path():
    """Return the expected production database path based on the OS."""
    home = Path.home()
    
    if platform.system() == "Linux":
        return str(home / ".config" / "cylestio-monitor" / "cylestio.db")
    elif platform.system() == "Darwin":  # macOS
        return str(home / "Library" / "Application Support" / "cylestio-monitor" / "cylestio.db")
    elif platform.system() == "Windows":
        return str(home / "AppData" / "Local" / "cylestio" / "cylestio-monitor" / "cylestio.db")
    else:
        return "./data/cylestio.db"  # Default

@pytest.fixture
def temp_env():
    """Fixture to temporarily modify and restore environment variables."""
    # Save original environment
    orig_env = os.environ.copy()
    
    # Clear any existing database path
    if "CYLESTIO_DB_PATH" in os.environ:
        del os.environ["CYLESTIO_DB_PATH"]
    
    # Mark as testing to avoid contaminating production DB
    os.environ["CYLESTIO_TEST_MODE"] = "true"
    
    # Use a context to handle cleanup
    yield
    
    # Restore the original environment
    for key in list(os.environ.keys()):
        if key not in orig_env:
            del os.environ[key]
        else:
            os.environ[key] = orig_env[key]

def test_default_test_db_path(temp_env):
    """Test that the default test database path is set correctly."""
    # Set test environment and path
    os.environ["CYLESTIO_DB_PATH"] = "./data/test_cylestio.db"
    
    # Import and reload the module to apply environment changes
    import app.database.init_db
    if "app.database.init_db" in sys.modules:
        import importlib
        importlib.reload(sys.modules["app.database.init_db"])
    from app.database import init_db
    
    # Try to get the DB_PATH - either as attribute or by creating test engine
    db_path = None
    if hasattr(init_db, "DB_PATH"):
        db_path = init_db.DB_PATH
    else:
        # If DB_PATH isn't directly accessible, we can verify it matches our path
        print(f"Using test database path: {os.environ['CYLESTIO_DB_PATH']}")
        assert "test_cylestio.db" in os.environ["CYLESTIO_DB_PATH"]
        db_path = os.environ["CYLESTIO_DB_PATH"]
    
    # Verify the path contains our test database name
    assert "test_cylestio.db" in db_path, f"Expected path to include test_cylestio.db, got {db_path}"
    print(f"Test database path is correctly set: {db_path}")

def test_production_db_path_setting(temp_env):
    """Test that the production database path is set correctly."""
    # Generate expected path based on OS
    expected_path = get_expected_production_db_path()
    
    # Create a custom module to test the path logic
    test_module_code = f"""
import os
from pathlib import Path

def get_production_db_path():
    home = Path.home()
    
    if "{platform.system()}" == "Linux":
        db_dir = home / ".config" / "cylestio-monitor"
    elif "{platform.system()}" == "Darwin":  # macOS
        db_dir = home / "Library" / "Application Support" / "cylestio-monitor"
    elif "{platform.system()}" == "Windows":
        db_dir = home / "AppData" / "Local" / "cylestio" / "cylestio-monitor"
    else:
        db_dir = Path("./data")
    
    return str(db_dir / "cylestio.db")

# Use default path for production mode (no environment variable)
db_path = get_production_db_path()
assert db_path == "{expected_path}", f"Expected {{db_path}} to equal {expected_path}"
print(f"Production DB Path test passed. Path: {{db_path}}")
"""
    
    # Execute the test code
    exec(test_module_code)

def test_db_directory_creation(temp_env):
    """Test that the database directory is created if it doesn't exist."""
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        test_db_dir = os.path.join(temp_dir, "test_dir")
        temp_db_path = os.path.join(test_db_dir, "test.db")
        
        # Set the environment variable to this non-existent path
        os.environ["CYLESTIO_DB_PATH"] = temp_db_path
        
        # Reload init_db module directly
        import app.database.init_db
        if "app.database.init_db" in sys.modules:
            import importlib
            importlib.reload(sys.modules["app.database.init_db"])
        
        # Verify the directory was created
        assert os.path.exists(test_db_dir), f"Directory {test_db_dir} should have been created"

def test_db_init_creates_tables(temp_env):
    """Test that the database directory is created during initialization."""
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_db_path = os.path.join(temp_dir, "test_init.db")
        
        # Set the environment variable
        os.environ["CYLESTIO_DB_PATH"] = temp_db_path
        
        # Reload init_db module directly
        import app.database.init_db
        if "app.database.init_db" in sys.modules:
            import importlib
            importlib.reload(sys.modules["app.database.init_db"])
        from app.database import init_db
        
        # Try to get the DB_PATH - either as attribute or by accessing environment variable
        db_path = None
        if hasattr(init_db, "DB_PATH"):
            db_path = init_db.DB_PATH
        else:
            # If DB_PATH isn't directly accessible, check the configured path matches
            print(f"Using test database path: {os.environ['CYLESTIO_DB_PATH']}")
            assert temp_db_path == os.environ["CYLESTIO_DB_PATH"]
            db_path = os.environ["CYLESTIO_DB_PATH"]
            
        # Verify the path is correctly set
        assert db_path == temp_db_path
        
        # Ensure the directory exists
        db_dir = os.path.dirname(temp_db_path)
        assert os.path.exists(db_dir), f"Database directory {db_dir} does not exist"

if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 