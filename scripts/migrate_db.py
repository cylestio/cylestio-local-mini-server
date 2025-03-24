#!/usr/bin/env python
"""
Database Migration Script for Cylestio Monitor.

This script applies database migrations to ensure the schema
matches the current model definitions.
"""

import os
import sys
import glob
import sqlite3
import logging
import argparse
import re
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("db-migrate")

# Get project root
def get_project_root():
    """Get the absolute path to the project root directory."""
    return Path(__file__).parent.parent.absolute()

def get_db_path(db_name=None):
    """
    Get the path to the database file.
    
    Args:
        db_name: Optional name of the database file
        
    Returns:
        Path to the database file
    """
    # If DB name specified, use it
    if db_name:
        db_path = os.path.join(get_project_root(), "data", db_name)
    # Otherwise, use environment variable or default
    elif "CYLESTIO_DB_PATH" in os.environ:
        db_path = os.environ.get("CYLESTIO_DB_PATH")
    else:
        db_path = os.path.join(get_project_root(), "data", "cylestio.db")
    
    # For relative paths, make them absolute using project root
    if not os.path.isabs(db_path):
        db_path = os.path.join(get_project_root(), db_path)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    return db_path

def is_duplicate_column_error(error_msg):
    """
    Check if the SQLite error is about a duplicate column.
    
    Args:
        error_msg: The error message to check
        
    Returns:
        True if it's a duplicate column error, False otherwise
    """
    return "duplicate column name" in error_msg.lower()

def apply_migrations(db_path, force_rerun=False):
    """
    Apply any pending migrations to the database.
    
    Args:
        db_path: Path to the database file
        force_rerun: Whether to force re-running all migrations
    
    Returns:
        Number of migrations applied
    """
    # Connect to the database
    logger.info(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create migrations tracking table if it doesn't exist
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS migrations (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()
    
    # Get list of already applied migrations
    cursor.execute("SELECT name FROM migrations")
    applied_migrations = {row[0] for row in cursor.fetchall()}
    
    # Find all migration files
    migrations_dir = os.path.join(get_project_root(), "migrations")
    migration_files = sorted(glob.glob(os.path.join(migrations_dir, "*.sql")))
    
    # Apply pending migrations
    applied_count = 0
    
    for migration_file in migration_files:
        migration_name = os.path.basename(migration_file)
        
        # Skip if already applied and not forcing rerun
        if migration_name in applied_migrations and not force_rerun:
            logger.info(f"Skipping already applied migration: {migration_name}")
            continue
        
        # Apply the migration
        logger.info(f"Applying migration: {migration_name}")
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        # Split SQL into individual statements to handle them separately
        statements = [s.strip() for s in migration_sql.split(';') if s.strip()]
        
        try:
            # Begin transaction
            conn.execute("BEGIN TRANSACTION")
            
            # Execute each statement individually
            for statement in statements:
                if not statement:
                    continue
                
                try:
                    cursor.execute(statement)
                except sqlite3.OperationalError as e:
                    error_msg = str(e)
                    
                    # Handle common errors gracefully
                    if is_duplicate_column_error(error_msg):
                        # This is likely an ALTER TABLE statement trying to add a column that already exists
                        # Extract the column name from the error message
                        match = re.search(r"duplicate column name:\s+(\w+)", error_msg)
                        column_name = match.group(1) if match else "unknown"
                        logger.warning(f"Column '{column_name}' already exists, skipping")
                        continue
                    else:
                        # Other errors are re-raised
                        raise
            
            # Track the migration as applied (update if rerunning)
            if migration_name in applied_migrations:
                cursor.execute(
                    "UPDATE migrations SET applied_at = CURRENT_TIMESTAMP WHERE name = ?",
                    (migration_name,)
                )
            else:
                cursor.execute(
                    "INSERT INTO migrations (name) VALUES (?)",
                    (migration_name,)
                )
            
            # Commit transaction
            conn.commit()
            applied_count += 1
            logger.info(f"Successfully applied migration: {migration_name}")
            
        except Exception as e:
            # Rollback transaction on error
            conn.rollback()
            logger.error(f"Error applying migration {migration_name}: {str(e)}")
            raise
    
    # Close the connection
    conn.close()
    
    return applied_count

def initialize_db(db_path):
    """
    Initialize the database with the current schema if it's empty.
    
    Args:
        db_path: Path to the database file
    
    Returns:
        True if database was initialized, False otherwise
    """
    # Check if the database exists and has tables
    if os.path.exists(db_path) and os.path.getsize(db_path) > 0:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        conn.close()
        
        if tables:
            logger.info("Database already exists and contains tables")
            return False
    
    # Database doesn't exist or is empty, initialize it
    logger.info(f"Initializing database schema at {db_path}")
    
    # Find the initialize schema SQL file
    init_file = os.path.join(get_project_root(), "migrations", "initialize_schema.sql")
    
    if not os.path.exists(init_file):
        logger.error(f"Initialization file not found: {init_file}")
        return False
    
    # Apply the initialization
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    with open(init_file, 'r') as f:
        init_sql = f.read()
    
    try:
        cursor.executescript(init_sql)
        
        # Create migrations tracking table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS migrations (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        # Mark the initialization migration as applied
        cursor.execute(
            "INSERT INTO migrations (name) VALUES (?)",
            (os.path.basename(init_file),)
        )
        
        conn.commit()
        logger.info("Database initialized successfully")
        return True
        
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Error initializing database: {str(e)}")
        raise
    finally:
        conn.close()

def main():
    """Main function to run the migration script."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Database migration tool for Cylestio Monitor")
    parser.add_argument("--db", help="Name of the database file in the data directory")
    parser.add_argument("--force-rerun", action="store_true", help="Force re-running all migrations")
    parser.add_argument("--init-only", action="store_true", help="Only initialize the database, don't run migrations")
    args = parser.parse_args()
    
    # Get database path
    db_path = get_db_path(args.db)
    
    try:
        # Initialize if needed
        initialized = initialize_db(db_path)
        
        if args.init_only:
            logger.info("Init-only mode, skipping migrations")
            return
        
        # Apply migrations
        applied_count = apply_migrations(db_path, args.force_rerun)
        
        # Report success
        if initialized:
            logger.info(f"Database initialized and {applied_count} migrations applied")
        else:
            logger.info(f"{applied_count} migrations applied")
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 