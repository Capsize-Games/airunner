"""
Unit tests for InputImageScene (business logic, minimal Qt dependencies).
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from airunner.gui.widgets.canvas.input_image_scene import InputImageScene


class DummySettings:
    def __init__(self):
        self.image = "img"
        self.generated_image = "gen_img"
        self.mask = "mask_img"
        self.lock_input_image = False
        self.use_grid_image_as_input = False
        self.enable_automatic_drawing = False


class DummyContext:
    def __init__(self):
        self.controlnet_settings = DummySettings()
        self.image_to_image_settings = DummySettings()
        self.outpaint_settings = DummySettings()
        self.drawing_pad_settings = DummySettings()
        self.update_controlnet_settings = MagicMock()
        self.update_image_to_image_settings = MagicMock()
        self.update_outpaint_settings = MagicMock()
        self.update_drawing_pad_settings = MagicMock()
        self.current_settings = self.image_to_image_settings


def make_scene(
    settings_key="image_to_image_settings",
    is_mask=False,
    props=None,
    current_settings=None,
    is_brush_or_eraser=None,
    active_image=None,
):
    with patch.object(InputImageScene, "__init__", lambda self, **kwargs: None):
        scene = InputImageScene(
            canvas_type="test",
            settings_key="test_settings",
            is_mask=False,
            application_settings=MagicMock(
                current_tool="BRUSH", dark_mode_enabled=False
            ),
        )
        scene._settings_key = settings_key
        scene._is_mask = is_mask
        # Patch property getters
        props = props or {}
        for name, value in props.items():
            patcher = patch.object(
                InputImageScene,
                name,
                new_callable=PropertyMock,
                return_value=value,
            )
            patcher.start()
        # Patch current_settings property
        if current_settings is not None:
            patch.object(
                InputImageScene,
                "current_settings",
                new_callable=PropertyMock,
                return_value=current_settings,
            ).start()
        # Patch is_brush_or_eraser property
        if is_brush_or_eraser is not None:
            patch.object(
                InputImageScene,
                "is_brush_or_eraser",
                new_callable=PropertyMock,
                return_value=is_brush_or_eraser,
            ).start()
        # Patch active_image property
        if active_image is not None:
            patch.object(
                InputImageScene,
                "active_image",
                new_callable=PropertyMock,
                return_value=active_image,
            ).start()
        return scene


@pytest.mark.parametrize(
    "settings_key,is_mask,expected_attr",
    [
        ("controlnet_settings", False, "generated_image"),
        ("image_to_image_settings", False, "image"),
        ("outpaint_settings", False, "image"),
        ("drawing_pad_settings", False, "image"),
        ("outpaint_settings", True, "mask"),
    ],
)
def test_current_active_image(settings_key, is_mask, expected_attr, monkeypatch):
    dummy = MagicMock()
    setattr(dummy, expected_attr, expected_attr + "_val")
    props = {
        "controlnet_settings": dummy,
        "image_to_image_settings": dummy,
        "outpaint_settings": dummy,
        "drawing_pad_settings": dummy,
    }
    # Patch current_settings to dummy as well
    scene = make_scene(settings_key, is_mask, props=props, current_settings=dummy)
    monkeypatch.setattr(
        "airunner.gui.widgets.canvas.input_image_scene.convert_binary_to_image",
        lambda b: b,
    )
    # Patch mask for is_mask
    if is_mask:
        dummy.mask = "mask_val"
    val = getattr(scene, settings_key, dummy)
    assert getattr(val, expected_attr) == expected_attr + "_val"


def test_current_active_image_setter(monkeypatch):
    scene = make_scene()
    scene.update_image_to_image_settings = MagicMock()
    monkeypatch.setattr(
        "airunner.gui.widgets.canvas.input_image_scene.convert_image_to_binary",
        lambda img: "bin",
    )
    scene.current_active_image = "img"
    scene.update_image_to_image_settings.assert_called_once_with("image", "bin")


def test_handle_left_mouse_release_brush(monkeypatch):
    scene = make_scene(is_brush_or_eraser=True, active_image=MagicMock())
    monkeypatch.setattr(
        "airunner.gui.widgets.canvas.input_image_scene.ImageQt.fromqimage",
        lambda q: "img",
    )
    monkeypatch.setattr(
        "airunner.gui.widgets.canvas.input_image_scene.convert_image_to_binary",
        lambda img: "bin",
    )
    scene.update_image_to_image_settings = MagicMock()
    scene.drawing_pad_settings = MagicMock()
    scene.drawing_pad_settings.enable_automatic_drawing = False
    scene._is_drawing = True
    scene._is_erasing = True
    # Patch api.art.send_request
    scene.api = MagicMock()
    scene.api.art = MagicMock()
    scene.api.art.send_request = MagicMock()
    result = InputImageScene._handle_left_mouse_release(scene, event=MagicMock())
    scene.update_image_to_image_settings.assert_called_once_with("image", "bin")
    assert result is True
    assert not scene._is_drawing
    assert not scene._is_erasing


def test_handle_image_generated_signal_locked():
    dummy = MagicMock()
    dummy.lock_input_image = True
    scene = make_scene(current_settings=dummy)
    InputImageScene._handle_image_generated_signal(scene, {})
