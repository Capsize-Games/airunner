"""Tests for input image pinning and grid-link behavior."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

from PIL import Image

from airunner.components.art.gui.widgets.canvas import input_image
from airunner.components.art.gui.widgets.canvas.input_image import InputImage


def test_link_to_grid_image_can_skip_setting_sync():
    """Show-time sync should not persist grid-link state."""
    widget = SimpleNamespace(
        load_image_from_grid=Mock(),
    )

    InputImage._link_to_grid_image(
        widget,
        force_load=False,
        sync_settings=False,
    )

    widget.load_image_from_grid.assert_called_once_with(
        forced=False,
        sync_settings=False,
    )


def test_pin_toggle_on_captures_current_image_and_locks():
    """Pinning should freeze the visible source image."""
    widget = SimpleNamespace(
        _capture_current_input_image=Mock(),
        update_current_settings=Mock(),
        _update_scene_lock_state=Mock(),
    )

    InputImage.on_pin_image_toggled(widget, True)

    widget._capture_current_input_image.assert_called_once_with()
    widget.update_current_settings.assert_called_once_with(
        "lock_input_image",
        True,
    )
    widget._update_scene_lock_state.assert_called_once_with(True)


def test_pin_toggle_off_relinks_to_latest_grid_image():
    """Unpinning should return the widget to the live grid image."""
    widget = SimpleNamespace(
        _capture_current_input_image=Mock(),
        update_current_settings=Mock(),
        _update_scene_lock_state=Mock(),
        _link_to_grid_image=Mock(),
    )

    InputImage.on_pin_image_toggled(widget, False)

    widget._capture_current_input_image.assert_not_called()
    widget.update_current_settings.assert_called_once_with(
        "lock_input_image",
        False,
    )
    widget._update_scene_lock_state.assert_called_once_with(False)
    widget._link_to_grid_image.assert_called_once_with(force_load=True)


def test_capture_current_input_image_uses_displayed_preview():
    """Pinning should persist the already displayed preview image."""
    image_object = Image.new("RGB", (2, 2), color="red")
    widget = SimpleNamespace(
        is_mask=False,
        _get_displayed_image=Mock(return_value=image_object),
        _get_lock_source_image=Mock(),
        load_image_from_object=Mock(),
        _apply_current_settings_value=Mock(),
    )

    with patch.object(
        input_image,
        "convert_image_to_binary",
        return_value=b"binary-image",
    ):
        InputImage._capture_current_input_image(widget)

    widget._get_displayed_image.assert_called_once_with()
    widget._get_lock_source_image.assert_not_called()
    widget.load_image_from_object.assert_not_called()
    widget._apply_current_settings_value.assert_called_once_with(
        "image",
        b"binary-image",
    )


def test_grid_image_button_loads_current_grid_for_img2img():
    """The grid button should explicitly copy the current grid image."""
    widget = SimpleNamespace(
        settings_key="image_to_image_settings",
        load_image_from_grid=Mock(),
    )

    InputImage.on_grid_image_clicked(widget)

    widget.load_image_from_grid.assert_called_once_with(forced=True)


def test_sync_input_source_uses_grid_when_not_pinned():
    """Show-time sync should follow the grid by default when unpinned."""
    widget = SimpleNamespace(
        current_settings=SimpleNamespace(lock_input_image=False),
        should_follow_grid_updates=Mock(return_value=True),
        _sync_pin_button_state=Mock(),
        _update_scene_lock_state=Mock(),
        load_image_from_settings=Mock(),
        _link_to_grid_image=Mock(),
    )

    InputImage._sync_input_source(
        widget,
        force_grid_load=True,
        sync_settings=False,
    )

    widget._sync_pin_button_state.assert_called_once_with()
    widget.should_follow_grid_updates.assert_called_once_with()
    widget._update_scene_lock_state.assert_called_once_with(False)
    widget.load_image_from_settings.assert_not_called()
    widget._link_to_grid_image.assert_called_once_with(
        force_load=True,
        sync_settings=False,
    )


def test_load_image_from_grid_ignores_legacy_link_state_when_unpinned():
    """Unlocked widgets should still follow the grid without DB writes."""
    widget = SimpleNamespace(
        settings_key="image_to_image_settings",
        current_settings=SimpleNamespace(
            lock_input_image=False,
            use_grid_image_as_input=False,
            image=None,
        ),
        drawing_pad_settings=SimpleNamespace(image=None),
        should_follow_grid_updates=Mock(return_value=True),
        update_current_settings=Mock(),
        load_image_from_object=Mock(),
        _clear_scene_image=Mock(),
    )

    InputImage.load_image_from_grid(
        widget,
        forced=False,
        sync_settings=False,
    )

    widget.should_follow_grid_updates.assert_called_once_with()
    widget.update_current_settings.assert_not_called()
    widget._clear_scene_image.assert_called_once_with()