"""Pytest configuration for long_running module tests.

Sets up an in-memory SQLite database with the required tables for testing
project management without affecting the main application database.
"""

import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

# Import Base from our local module, not the shared one
from airunner.components.data.models.base import Base


@pytest.fixture(autouse=True, scope="function")
def test_database(monkeypatch, tmp_path):
    """Set up an isolated test database for each test.
    
    This fixture:
    1. Creates a new SQLite database file in a temp directory
    2. Patches AIRUNNER_DB_URL to point to it
    3. Resets the session manager to use the new URL
    4. Creates only the tables needed for long_running module
    5. Cleans up after the test
    """
    # Create isolated test database
    db_path = tmp_path / "test_long_running.db"
    test_db_url = f"sqlite:///{db_path}"
    
    # Patch the database URL before any database operations
    monkeypatch.setenv("AIRUNNER_DATABASE_URL", test_db_url)
    
    # Import and reset session manager to pick up new URL
    from airunner.components.data import session_manager
    session_manager.reset_engine()
    
    # Also patch the module-level setting
    import airunner.settings
    monkeypatch.setattr(airunner.settings, 'AIRUNNER_DB_URL', test_db_url)
    
    # Create engine
    engine = create_engine(test_db_url)
    
    # Import the models to ensure they're registered with Base
    from airunner.components.llm.long_running.data.project_state import (
        ProjectState,
        ProjectFeature,
        ProgressEntry,
        SessionState,
        DecisionMemory,
    )
    
    # Create only our specific tables, not all tables in Base.metadata
    # This avoids foreign key issues with other models in the app
    tables_to_create = [
        ProjectState.__table__,
        ProjectFeature.__table__,
        ProgressEntry.__table__,
        SessionState.__table__,
        DecisionMemory.__table__,
    ]
    
    for table in tables_to_create:
        table.create(engine, checkfirst=True)
    
    yield test_db_url
    
    # Cleanup
    engine.dispose()
    session_manager.reset_engine()
    
    # Remove the test database file
    if db_path.exists():
        db_path.unlink()
