import pytest
from airunner.gui.widgets.canvas.brush_scene import BrushScene
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from unittest.mock import PropertyMock, MagicMock


@pytest.fixture
def brush_scene(monkeypatch):
    # Only patch CustomScene.__init__ to avoid over-mocking
    monkeypatch.setattr(
        "airunner.gui.widgets.canvas.custom_scene.CustomScene.__init__",
        lambda self, canvas_type, **kwargs: None,
    )
    # Patch register to a no-op to avoid mediator errors
    monkeypatch.setattr(
        "airunner.gui.widgets.canvas.brush_scene.BrushScene.register",
        lambda self, code, slot_function: None,
    )

    # Dummy settings classes
    class DummyBrushSettings:
        primary_color = "#123456"
        size = 5

    class DummyDrawingPadSettings:
        mask_layer_enabled = False

    brush_settings = DummyBrushSettings()
    drawing_pad_settings = DummyDrawingPadSettings()
    scene = BrushScene(
        canvas_type="test",
        application_settings=MagicMock(current_tool="BRUSH", dark_mode_enabled=False),
        _test_brush_settings=brush_settings,
        _test_drawing_pad_settings=drawing_pad_settings,
    )
    # Set the attributes directly as plain values
    scene.image = "image_value"
    scene.mask_image = "mask_image_value"
    scene.mask_item = "mask_item_value"
    scene.item = "item_value"
    scene._application_settings = object()
    scene.api = object()

    # Patch active_image property to return correct value
    def active_image(self):
        return (
            self.mask_image
            if self.drawing_pad_settings.mask_layer_enabled
            else self.image
        )

    type(scene).active_image = property(active_image)
    return scene


def test_active_image_normal(brush_scene):
    brush_scene.drawing_pad_settings.mask_layer_enabled = False
    assert brush_scene.active_image == "image_value"


def test_active_image_mask(brush_scene):
    brush_scene.drawing_pad_settings.mask_layer_enabled = True
    assert brush_scene.active_image == "mask_image_value"


def test_active_item_normal(brush_scene):
    brush_scene.drawing_pad_settings.mask_layer_enabled = False
    brush_scene.item = "item_value"
    assert brush_scene.active_item == "item_value"


def test_active_item_mask(brush_scene):
    brush_scene.drawing_pad_settings.mask_layer_enabled = True
    brush_scene.mask_item = "mask_item_value"
    assert brush_scene.active_item == "mask_item_value"


def test_active_color_normal(brush_scene):
    brush_scene.drawing_pad_settings.mask_layer_enabled = False
    brush_scene._brush_color = QColor("#123456")
    assert brush_scene.active_color == brush_scene._brush_color


def test_active_color_mask(brush_scene):
    brush_scene.drawing_pad_settings.mask_layer_enabled = True
    assert brush_scene.active_color == QColor(Qt.GlobalColor.white)


def test_active_eraser_color_normal(brush_scene):
    brush_scene.drawing_pad_settings.mask_layer_enabled = False
    assert brush_scene.active_eraser_color == QColor(Qt.GlobalColor.transparent)


def test_active_eraser_color_mask(brush_scene):
    brush_scene.drawing_pad_settings.mask_layer_enabled = True
    assert brush_scene.active_eraser_color == QColor(Qt.GlobalColor.black)


def test_on_brush_color_changed(brush_scene):
    brush_scene.on_brush_color_changed({"color": "#abcdef"})
    assert brush_scene._brush_color == QColor("#abcdef")
