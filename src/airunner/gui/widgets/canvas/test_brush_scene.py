"""
Unit tests for BrushScene mouse release event and DrawingPadSettings save logic.
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from PySide6.QtCore import Qt
from PIL import ImageQt, Image
from airunner.gui.widgets.canvas.brush_scene import BrushScene


@pytest.fixture
def mock_drawing_pad_settings(monkeypatch):
    mock_settings = MagicMock()
    mock_settings.mask_layer_enabled = False
    mock_settings.save = MagicMock()
    monkeypatch.setattr(
        "airunner.data.models.DrawingPadSettings.objects.first",
        lambda: mock_settings,
    )
    return mock_settings


@pytest.fixture
def brush_scene(monkeypatch, mock_drawing_pad_settings):
    # Patch all PySide6/Qt parent initializers to prevent C++ code execution
    monkeypatch.setattr(
        "airunner.gui.widgets.canvas.custom_scene.CustomScene.__init__",
        lambda self, canvas_type: None,
    )
    monkeypatch.setattr(
        "airunner.gui.widgets.canvas.custom_scene.SettingsMixin.__init__",
        lambda self: None,
    )
    monkeypatch.setattr(
        "airunner.utils.application.mediator_mixin.MediatorMixin.__init__",
        lambda self: None,
    )
    # Patch register to a no-op to avoid mediator dependency
    monkeypatch.setattr(
        "airunner.gui.widgets.canvas.brush_scene.BrushScene.register",
        lambda self, code, slot_function: None,
    )
    # Create BrushScene instance without running real parent initializers
    scene = BrushScene(canvas_type="test")
    # Mock all required attributes
    scene.api = MagicMock()
    scene.api.art.canvas.generate_mask = MagicMock()
    scene.api.art.canvas.image_updated = MagicMock()
    scene.update_drawing_pad_settings = MagicMock()
    scene.mask_image = MagicMock()
    # Patch the drawing_pad_settings, active_image, and current_tool properties to return the mocks
    type(scene).drawing_pad_settings = PropertyMock(
        return_value=mock_drawing_pad_settings
    )
    type(scene).active_image = PropertyMock(return_value=MagicMock())
    type(scene).current_tool = PropertyMock(return_value=MagicMock())
    return scene


@patch("airunner.data.models.DrawingPadSettings.objects.first")
@patch("PIL.ImageQt.fromqimage", return_value=MagicMock(spec=Image.Image))
def test_handle_left_mouse_release_calls_save(
    mock_fromqimage, mock_first, brush_scene, mock_drawing_pad_settings
):
    mock_first.return_value = mock_drawing_pad_settings
    # Simulate event
    event = MagicMock()
    brush_scene._handle_left_mouse_release(event)
    # Should call save on the model
    assert mock_drawing_pad_settings.save.called
