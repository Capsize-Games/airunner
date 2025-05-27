"""
Unit and functional tests for InputImage widget.
Covers: signal connection, auto-refresh, image import, deletion, and UI state.
"""

import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication
from airunner.gui.widgets.canvas.input_image import InputImage

# Mark GUI-dependent tests as skipped due to segfaults in headless/CI environments
pytestmark = pytest.mark.skip(
    "GUI-dependent test: causes segfault in headless/CI environments (QFileDialog)"
)


@pytest.fixture
def input_image_widget(qtbot):
    # Patch dependencies and settings
    with patch(
        "airunner.gui.widgets.canvas.input_image.BaseWidget.__init__",
        lambda self, *a, **k: None,
    ):
        widget = InputImage(settings_key="image_to_image_settings")
        widget.logger = MagicMock()
        widget.api = MagicMock()
        widget.current_settings = MagicMock()
        widget.current_settings.use_grid_image_as_input = False
        widget.current_settings.lock_input_image = False
        widget.current_settings.enabled = True
        widget.current_settings.strength = 1.0
        widget.ui = MagicMock()
        widget.ui.image_container = MagicMock()
        widget.ui.strength_slider_widget = MagicMock()
        widget.ui.controlnet_settings = MagicMock()
        widget.ui.mask_blur_slider_widget = MagicMock()
        widget.ui.EnableSwitch = MagicMock()
        widget.ui.link_to_grid_image_button = MagicMock()
        widget.ui.lock_input_image_button = MagicMock()
        widget._scene = MagicMock()
        yield widget


def test_signal_connection_on_link_toggle(input_image_widget):
    # Use a mock canvas_widget with a mock signal
    class DummySignal:
        def __init__(self):
            self.connect = MagicMock()
            self.disconnect = MagicMock()

    class DummyCanvasWidget:
        drawing_pad_image_changed = DummySignal()

    canvas_widget = DummyCanvasWidget()
    widget = InputImage(
        settings_key="image_to_image_settings", canvas_widget=canvas_widget
    )
    widget.logger = MagicMock()
    widget.current_settings = MagicMock()
    widget.current_settings.use_grid_image_as_input = True
    widget.current_settings.lock_input_image = False
    widget._on_drawing_pad_image_changed = MagicMock()
    # Should connect signal
    widget._update_drawing_pad_image_signal()
    canvas_widget.drawing_pad_image_changed.connect.assert_called_with(
        widget._on_drawing_pad_image_changed
    )
    # Should disconnect signal
    widget.current_settings.use_grid_image_as_input = False
    widget._update_drawing_pad_image_signal()
    canvas_widget.drawing_pad_image_changed.disconnect.assert_called_with(
        widget._on_drawing_pad_image_changed
    )


def test_auto_refresh_on_drawing_pad_change(input_image_widget):
    widget = input_image_widget
    widget.current_settings.use_grid_image_as_input = True
    widget.current_settings.lock_input_image = False
    widget.load_image_from_grid = MagicMock()
    widget._on_drawing_pad_image_changed()
    widget.load_image_from_grid.assert_called_with(forced=True)

    widget.current_settings.lock_input_image = True
    widget.load_image_from_grid.reset_mock()
    widget._on_drawing_pad_image_changed()
    widget.load_image_from_grid.assert_not_called()


def test_import_image_opens_dialog(input_image_widget, monkeypatch):
    widget = input_image_widget
    called = {}

    def fake_getOpenFileName(*a, **k):
        called["called"] = True
        return ("/tmp/fake.png", "")

    monkeypatch.setattr(
        "airunner.gui.widgets.canvas.input_image.QFileDialog.getOpenFileName",
        fake_getOpenFileName,
    )
    widget.load_image = MagicMock()
    widget.import_image()
    assert called["called"]
    widget.load_image.assert_called_with("/tmp/fake.png")


def test_delete_image_clears_scene(input_image_widget):
    widget = input_image_widget
    widget.settings_key = "image_to_image_settings"
    widget.is_mask = False
    widget.update_current_settings = MagicMock()
    widget._scene = MagicMock()
    widget.ui.image_container = MagicMock()
    widget.load_image_from_settings = MagicMock()
    widget.delete_image()
    widget.update_current_settings.assert_called_with("image", None)
    widget._scene.clear.assert_called()
    widget.load_image_from_settings.assert_called()


def test_load_image_from_object_handles_none(input_image_widget):
    widget = input_image_widget
    widget.logger = MagicMock()
    widget._scene = MagicMock()
    widget.load_image_from_object(None)
    widget.logger.warning.assert_called()


def test_input_image_scene_current_active_image_and_setter(monkeypatch):
    from airunner.gui.widgets.canvas.input_image_scene import InputImageScene

    scene = InputImageScene(
        canvas_type="input_image",
        settings_key="image_to_image_settings",
        is_mask=False,
        application_settings=MagicMock(current_tool="BRUSH", dark_mode_enabled=False),
    )
    # Patch settings and attributes
    scene.drawing_pad_settings = MagicMock(mask=b"binarymask")
    scene.controlnet_settings = MagicMock(generated_image=b"binarygen")
    scene.outpaint_settings = MagicMock(image=b"binaryoutpaint")
    scene.image_to_image_settings = MagicMock(image=b"binaryimg2img")
    scene.current_settings = MagicMock(image=b"binarydefault")
    scene.use_generated_image = False
    # Should return image for each settings_key
    monkeypatch.setattr(
        "airunner.utils.image.convert_binary_to_image", lambda b: f"img:{b}"
    )
    scene._is_mask = True
    assert scene.current_active_image == "img:binarymask"
    scene._is_mask = False
    scene._settings_key = "controlnet_settings"
    scene.use_generated_image = True
    assert scene.current_active_image == "img:binarygen"
    scene._settings_key = "outpaint_settings"
    assert scene.current_active_image == "img:binaryoutpaint"
    scene._settings_key = "image_to_image_settings"
    assert scene.current_active_image == "img:binaryimg2img"
    scene._settings_key = "drawing_pad_settings"
    assert scene.current_active_image == "img:binarydefault"
    # Test setter
    called = {}

    def fake_update(key, val):
        called[key] = val

    scene.update_drawing_pad_settings = fake_update
    scene.update_controlnet_settings = fake_update
    scene.update_outpaint_settings = fake_update
    scene.update_image_to_image_settings = fake_update
    scene._update_current_settings = fake_update
    monkeypatch.setattr(
        "airunner.utils.image.convert_image_to_binary", lambda i: f"bin:{i}"
    )
    scene._is_mask = True
    scene.current_active_image = "img"
    assert called["mask"] == "bin:img"
    scene._is_mask = False
    scene._settings_key = "controlnet_settings"
    scene.use_generated_image = True
    scene.current_active_image = "img"
    assert called["generated_image"] == "bin:img"
    scene._settings_key = "outpaint_settings"
    scene.current_active_image = "img"
    assert called["image"] == "bin:img"
    scene._settings_key = "image_to_image_settings"
    scene.current_active_image = "img"
    assert called["image"] == "bin:img"
    scene._settings_key = "drawing_pad_settings"
    scene.current_active_image = "img"
    assert called["image"] == "bin:img"


def test_input_image_scene_handle_left_mouse_release(monkeypatch):
    from airunner.gui.widgets.canvas.input_image_scene import InputImageScene

    scene = InputImageScene(
        canvas_type="input_image",
        settings_key="image_to_image_settings",
        is_mask=False,
        application_settings=MagicMock(current_tool="BRUSH", dark_mode_enabled=False),
    )
    scene.is_brush_or_eraser = True
    scene.active_image = MagicMock()
    scene.drawing_pad_settings = MagicMock(enable_automatic_drawing=False)
    scene.update_drawing_pad_settings = MagicMock()
    scene.update_controlnet_settings = MagicMock()
    scene.update_outpaint_settings = MagicMock()
    scene.update_image_to_image_settings = MagicMock()
    scene._is_mask = True
    monkeypatch.setattr(
        "airunner.utils.image.convert_image_to_binary", lambda i: b"bin"
    )
    monkeypatch.setattr("PIL.ImageQt.fromqimage", lambda q: "pilimg")
    event = MagicMock()
    ret = scene._handle_left_mouse_release(event)
    assert ret is True
    scene._is_mask = False
    scene.settings_key = "controlnet_settings"
    scene.use_generated_image = True
    ret = scene._handle_left_mouse_release(event)
    assert ret is True
    scene.settings_key = "outpaint_settings"
    ret = scene._handle_left_mouse_release(event)
    assert ret is True
    scene.settings_key = "image_to_image_settings"
    ret = scene._handle_left_mouse_release(event)
    assert ret is True
    # Test with enable_automatic_drawing
    scene.drawing_pad_settings.enable_automatic_drawing = True
    scene.api = MagicMock()
    scene.api.art.send_request = MagicMock()
    ret = scene._handle_left_mouse_release(event)
    scene.api.art.send_request.assert_called()


def test_input_image_scene_handle_image_generated_signal():
    from airunner.gui.widgets.canvas.input_image_scene import InputImageScene

    scene = InputImageScene(
        canvas_type="input_image",
        settings_key="image_to_image_settings",
        is_mask=False,
        application_settings=MagicMock(current_tool="BRUSH", dark_mode_enabled=False),
    )
    scene.current_settings = MagicMock(lock_input_image=False)
    scene._handle_image_generated_signal = MagicMock()
    # Should call super if not locked
    InputImageScene._handle_image_generated_signal.__wrapped__(scene, {})
    # Should not call super if locked
    scene.current_settings.lock_input_image = True
    InputImageScene._handle_image_generated_signal.__wrapped__(scene, {})


def test_input_image_load_image_from_grid_headless():
    widget = InputImage(settings_key="image_to_image_settings", test_mode=True)
    widget.update_current_settings = MagicMock()
    widget.load_image_from_grid()
    widget.update_current_settings.assert_called_with("image", "fake_grid_image")


def test_input_image_load_image_headless():
    widget = InputImage(settings_key="image_to_image_settings", test_mode=True)
    widget.update_current_settings = MagicMock()
    widget.load_image("/tmp/fake.png")
    widget.update_current_settings.assert_called_with("image", "fake_binary")


def test_input_image_import_image_headless(monkeypatch):
    widget = InputImage(settings_key="image_to_image_settings", test_mode=True)
    widget.load_image = MagicMock()
    monkeypatch.setattr(
        "airunner.gui.widgets.canvas.input_image.QFileDialog.getOpenFileName",
        lambda *a, **k: ("/tmp/fake.png", ""),
    )
    widget.import_image()
    widget.load_image.assert_called_with("/tmp/fake.png")


def test_input_image_delete_image_headless():
    widget = InputImage(settings_key="image_to_image_settings", test_mode=True)
    widget.update_current_settings = MagicMock()
    widget.delete_image()
    widget.update_current_settings.assert_called_with("image", None)


def test_input_image_lock_and_link_signal_management():
    widget = InputImage(settings_key="image_to_image_settings", test_mode=True)
    widget.current_settings = MagicMock()
    widget.current_settings.use_grid_image_as_input = True
    widget.current_settings.lock_input_image = False
    widget.api = MagicMock()
    widget.api.art = MagicMock()
    widget.api.art.canvas = MagicMock()
    widget.api.art.canvas.drawing_pad_image_changed = MagicMock()
    widget._on_drawing_pad_image_changed = MagicMock()
    widget._update_drawing_pad_image_signal()
    widget.api.art.canvas.drawing_pad_image_changed.connect.assert_called_with(
        widget._on_drawing_pad_image_changed
    )
    widget.current_settings.use_grid_image_as_input = False
    widget._update_drawing_pad_image_signal()
    widget.api.art.canvas.drawing_pad_image_changed.disconnect.assert_called()


def test_input_image_error_handling_in_close_event():
    widget = InputImage(settings_key="image_to_image_settings", test_mode=True)
    widget._scene = MagicMock()
    widget.ui = MagicMock()
    widget.ui.image_container = MagicMock()
    widget.api = MagicMock()
    widget.api.art = MagicMock()
    widget.api.art.canvas = MagicMock()
    widget.api.art.canvas.drawing_pad_image_changed = MagicMock()
    widget.logger = MagicMock()
    # Simulate error in scene clear
    widget._scene.clear.side_effect = Exception("fail")
    widget.closeEvent(MagicMock())
    widget.logger.error.assert_called()


def test_update_drawing_pad_image_signal_disconnect_and_connect(monkeypatch):
    from airunner.gui.widgets.canvas.input_image import InputImage

    widget = InputImage(settings_key="image_to_image_settings", test_mode=True)
    widget.logger = MagicMock()
    widget.current_settings = MagicMock()
    widget.current_settings.use_grid_image_as_input = True
    widget.current_settings.lock_input_image = False
    widget.api = MagicMock()
    widget.api.art = MagicMock()
    widget.api.art.canvas = MagicMock()
    # Simulate signal with disconnect/connect
    signal = MagicMock()
    widget.api.art.canvas.drawing_pad_image_changed = signal
    widget._on_drawing_pad_image_changed = MagicMock()
    widget._update_drawing_pad_image_signal()
    signal.disconnect.assert_called_with(widget._on_drawing_pad_image_changed)
    signal.connect.assert_called_with(widget._on_drawing_pad_image_changed)
    widget.logger.debug.assert_any_call("Connected drawing_pad_image_changed signal.")


def test_update_drawing_pad_image_signal_disconnect_typeerror(monkeypatch):
    from airunner.gui.widgets.canvas.input_image import InputImage

    widget = InputImage(settings_key="image_to_image_settings", test_mode=True)
    widget.logger = MagicMock()
    widget.current_settings = MagicMock()
    widget.current_settings.use_grid_image_as_input = True
    widget.current_settings.lock_input_image = False
    widget.api = MagicMock()
    widget.api.art = MagicMock()
    widget.api.art.canvas = MagicMock()
    signal = MagicMock()
    signal.disconnect.side_effect = TypeError("fail disconnect")
    widget.api.art.canvas.drawing_pad_image_changed = signal
    widget._on_drawing_pad_image_changed = MagicMock()
    widget._update_drawing_pad_image_signal()
    widget.logger.debug.assert_any_call(
        "Signal disconnect failed or not connected: fail disconnect"
    )


def test_update_drawing_pad_image_signal_disconnect_runtimeerror(monkeypatch):
    from airunner.gui.widgets.canvas.input_image import InputImage

    widget = InputImage(settings_key="image_to_image_settings", test_mode=True)
    widget.logger = MagicMock()
    widget.current_settings = MagicMock()
    widget.current_settings.use_grid_image_as_input = True
    widget.current_settings.lock_input_image = False
    widget.api = MagicMock()
    widget.api.art = MagicMock()
    widget.api.art.canvas = MagicMock()
    signal = MagicMock()
    signal.disconnect.side_effect = RuntimeError("fail disconnect")
    widget.api.art.canvas.drawing_pad_image_changed = signal
    widget._on_drawing_pad_image_changed = MagicMock()
    widget._update_drawing_pad_image_signal()
    widget.logger.debug.assert_any_call(
        "Signal disconnect failed or not connected: fail disconnect"
    )


def test_update_drawing_pad_image_signal_disconnect_other_exception(
    monkeypatch,
):
    from airunner.gui.widgets.canvas.input_image import InputImage

    widget = InputImage(settings_key="image_to_image_settings", test_mode=True)
    widget.logger = MagicMock()
    widget.current_settings = MagicMock()
    widget.current_settings.use_grid_image_as_input = True
    widget.current_settings.lock_input_image = False
    widget.api = MagicMock()
    widget.api.art = MagicMock()
    widget.api.art.canvas = MagicMock()
    signal = MagicMock()
    signal.disconnect.side_effect = Exception("fail disconnect")
    widget.api.art.canvas.drawing_pad_image_changed = signal
    widget._on_drawing_pad_image_changed = MagicMock()
    widget._update_drawing_pad_image_signal()
    widget.logger.error.assert_any_call(
        "Unexpected error during signal disconnect: fail disconnect",
        exc_info=True,
    )


def test_update_drawing_pad_image_signal_connect_exception(monkeypatch):
    from airunner.gui.widgets.canvas.input_image import InputImage

    widget = InputImage(settings_key="image_to_image_settings", test_mode=True)
    widget.logger = MagicMock()
    widget.current_settings = MagicMock()
    widget.current_settings.use_grid_image_as_input = True
    widget.current_settings.lock_input_image = False
    widget.api = MagicMock()
    widget.api.art = MagicMock()
    widget.api.art.canvas = MagicMock()
    signal = MagicMock()
    signal.connect.side_effect = Exception("fail connect")
    widget.api.art.canvas.drawing_pad_image_changed = signal
    widget._on_drawing_pad_image_changed = MagicMock()
    widget._update_drawing_pad_image_signal()
    widget.logger.error.assert_any_call(
        "Error connecting drawing_pad_image_changed: fail connect",
        exc_info=True,
    )


def test_update_drawing_pad_image_signal_not_connecting(monkeypatch):
    from airunner.gui.widgets.canvas.input_image import InputImage

    widget = InputImage(settings_key="image_to_image_settings", test_mode=True)
    widget.logger = MagicMock()
    widget.current_settings = MagicMock()
    widget.current_settings.use_grid_image_as_input = False
    widget.current_settings.lock_input_image = True
    widget.api = MagicMock()
    widget.api.art = MagicMock()
    widget.api.art.canvas = MagicMock()
    signal = MagicMock()
    widget.api.art.canvas.drawing_pad_image_changed = signal
    widget._on_drawing_pad_image_changed = MagicMock()
    widget._update_drawing_pad_image_signal()
    widget.logger.debug.assert_any_call(
        "Not connecting drawing_pad_image_changed: link or lock state."
    )
