"""Pytest configuration and shared fixtures for canvas widget tests.

This module provides test database setup and shared fixtures for testing
canvas widgets without affecting the production database.

PERFORMANCE NOTE:
Tests load fast because we use in-memory database. The main slowdown is
importing CustomScene which pulls in LLM utilities (inflect takes 1.3s).
This is a code organization issue to fix later.
"""

import pytest
import sys
from unittest.mock import MagicMock
from PySide6.QtWidgets import QApplication
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from airunner.components.data.models.base import Base


# Speed up tests by mocking slow-to-import modules that aren't needed for unit tests
@pytest.fixture(scope="session", autouse=True)
def mock_slow_imports():
    """Mock slow-importing modules that aren't needed for canvas unit tests."""
    # Mock inflect (takes 1.3s to import)
    # It's only used by LLM text preprocessing, not needed for canvas tests
    if "inflect" not in sys.modules:
        sys.modules["inflect"] = MagicMock()
    yield


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for the test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    # Don't quit - let pytest handle cleanup


@pytest.fixture(scope="session")
def test_db_engine():
    """Create SQLAlchemy engine with in-memory database for speed."""
    # Use in-memory SQLite database - MUCH faster than disk
    engine = create_engine("sqlite:///:memory:", echo=False)

    # Create all tables
    Base.metadata.create_all(engine)

    yield engine

    engine.dispose()


@pytest.fixture(scope="function")
def test_db_session(test_db_engine):
    """Create a clean database session for each test."""
    connection = test_db_engine.connect()
    transaction = connection.begin()

    Session = scoped_session(
        sessionmaker(bind=connection, expire_on_commit=False)
    )
    session = Session()

    yield session

    # Rollback and cleanup
    session.close()
    Session.remove()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def override_db_url(monkeypatch):
    """Override database URL to use in-memory database."""
    db_url = "sqlite:///:memory:"
    monkeypatch.setenv("AIRUNNER_DATABASE_URL", db_url)
    # Also patch the settings module constant
    from airunner import settings

    monkeypatch.setattr(settings, "AIRUNNER_DB_URL", db_url)
    return db_url


@pytest.fixture(scope="function")
def mock_scene_with_settings(qapp, monkeypatch):
    """Create CustomScene with mocked settings for unit tests.

    This fixture provides a fully initialized CustomScene that doesn't
    require database access. All settings are mocked to return safe defaults.
    """
    from unittest.mock import Mock, PropertyMock
    from airunner.components.art.gui.widgets.canvas.custom_scene import (
        CustomScene,
    )

    # Create scene
    scene = CustomScene(canvas_type="image")

    # Mock settings to avoid database dependency
    mock_settings = Mock()
    mock_settings.image = None
    mock_settings.lock_input_image = False
    mock_settings.x_pos = 0
    mock_settings.y_pos = 0

    # Mock the current_settings property
    type(scene).current_settings = PropertyMock(return_value=mock_settings)

    # Mock drawing_pad_settings
    mock_drawing_pad = Mock()
    mock_drawing_pad.x_pos = 0
    mock_drawing_pad.y_pos = 0
    type(scene).drawing_pad_settings = PropertyMock(
        return_value=mock_drawing_pad
    )

    # Mock active_grid_settings
    mock_grid = Mock()
    mock_grid.pos_x = 0
    mock_grid.pos_y = 0
    type(scene).active_grid_settings = PropertyMock(return_value=mock_grid)

    return scene


@pytest.fixture(scope="function")
def mock_image():
    """Create a standard test PIL Image."""
    from PIL import Image

    return Image.new("RGBA", (1024, 1024), (255, 0, 0, 255))


@pytest.fixture(scope="function")
def mock_small_image():
    """Create a small test PIL Image for performance tests."""
    from PIL import Image

    return Image.new("RGBA", (64, 64), (0, 255, 0, 255))


@pytest.fixture(scope="function")
def mock_qimage():
    """Create a standard test QImage."""
    from PySide6.QtGui import QImage

    qimage = QImage(256, 256, QImage.Format.Format_ARGB32)
    qimage.fill(0xFF0000FF)  # Red
    return qimage
