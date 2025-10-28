"""Pytest configuration for draggables tests."""

import pytest
from unittest.mock import Mock, PropertyMock
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for the test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    # Don't quit - let pytest handle cleanup


@pytest.fixture(scope="function")
def mock_scene_with_settings(qapp):
    """Create CustomScene with mocked settings for unit tests.

    This fixture provides a fully initialized CustomScene that doesn't
    require database access. All settings are mocked to return safe defaults.
    """
    from airunner.components.art.gui.widgets.canvas.custom_scene import (
        CustomScene,
    )

    # Create scene
    scene = CustomScene(canvas_type="image")

    # Mock settings to avoid database dependency
    mock_app_settings = Mock()
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
    mock_drawing_pad.snap_to_grid = False
    mock_drawing_pad.grid_size = 10
    type(scene).drawing_pad_settings = PropertyMock(
        return_value=mock_drawing_pad
    )
    mock_app_settings.drawingpad_settings = mock_drawing_pad

    # Mock active_grid_settings
    mock_grid = Mock()
    mock_grid.pos_x = 0
    mock_grid.pos_y = 0
    type(scene).active_grid_settings = PropertyMock(return_value=mock_grid)

    return scene, mock_app_settings
