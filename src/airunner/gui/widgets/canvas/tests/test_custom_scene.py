"""
Unit tests for CustomScene business logic (headless, no real Qt GUI).
"""

import pytest

pytest.skip("Skipping CustomScene GUI tests in headless mode.", allow_module_level=True)
from unittest.mock import MagicMock, patch, PropertyMock
from airunner.gui.widgets.canvas.custom_scene import CustomScene


@pytest.fixture
def mock_custom_scene():
    with patch(
        "airunner.gui.widgets.canvas.custom_scene.get_qsettings",
        return_value=MagicMock(),
    ), patch("airunner.gui.widgets.canvas.custom_scene.QGraphicsScene", MagicMock):
        # Use a real AppSettings object for business logic
        class AppSettings:
            def __init__(self):
                self.current_tool = "brush"

        app_settings = AppSettings()
        scene = CustomScene(
            canvas_type="brush",
            application_settings=MagicMock(
                current_tool="BRUSH", dark_mode_enabled=False
            ),
        )
        # Patch only the property on the instance
        type(scene).application_settings = PropertyMock(return_value=app_settings)
        return scene


def test_current_tool_property(mock_custom_scene):
    from airunner.enums import CanvasToolName

    # Test with valid enum string
    mock_custom_scene.application_settings.current_tool = "brush"
    assert mock_custom_scene.current_tool == CanvasToolName.BRUSH
    # Test with None
    mock_custom_scene.application_settings.current_tool = None
    assert mock_custom_scene.current_tool is None
    # Test with invalid value
    mock_custom_scene.application_settings.current_tool = "not_a_tool"
    assert mock_custom_scene.current_tool is None
