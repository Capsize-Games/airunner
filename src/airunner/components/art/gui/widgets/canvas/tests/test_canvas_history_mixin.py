"""Unit tests for CanvasHistoryMixin undo/redo functionality."""

import pytest
from unittest.mock import MagicMock

from airunner.components.art.gui.widgets.canvas.custom_scene import CustomScene


@pytest.fixture
def history_scene(qapp, mock_scene_with_settings):
    """Create a scene with history mixin for testing."""
    scene = mock_scene_with_settings
    scene.undo_history = []
    scene.redo_history = []
    scene.api = MagicMock()
    scene.api.art.canvas.update_history = MagicMock()
    scene.api.art.canvas.update_image_positions = MagicMock()
    scene._update_canvas_memory_allocation = MagicMock()
    scene._apply_layer_structure = MagicMock()
    scene._apply_layer_state = MagicMock()
    scene._capture_layer_state = CustomScene._capture_layer_state.__get__(
        scene, CustomScene
    )
    scene.on_action_undo_signal = CustomScene.on_action_undo_signal.__get__(
        scene, CustomScene
    )
    scene.on_action_redo_signal = CustomScene.on_action_redo_signal.__get__(
        scene, CustomScene
    )
    scene.on_clear_history_signal = (
        CustomScene.on_clear_history_signal.__get__(scene, CustomScene)
    )
    scene._apply_history_entry = CustomScene._apply_history_entry.__get__(
        scene, CustomScene
    )
    scene._clear_history = MagicMock()
    scene._refresh_layer_display = MagicMock()
    scene.update = MagicMock()

    # Mock views
    mock_view = MagicMock()
    mock_view.updateImagePositions = MagicMock()
    mock_view.viewport().update = MagicMock()
    mock_view.update = MagicMock()
    scene.views = MagicMock(return_value=[mock_view])

    return scene


class TestHistoryClear:
    """Test history clearing functionality."""

    def test_clear_history_signal_calls_clear_method(self, history_scene):
        """Test that clear history signal calls _clear_history."""
        history_scene.on_clear_history_signal()

        history_scene._clear_history.assert_called_once()


class TestUndoFunctionality:
    """Test undo operation."""

    def test_undo_with_empty_history_does_nothing(self, history_scene):
        """Test undo with no history entries."""
        assert len(history_scene.undo_history) == 0

        history_scene.on_action_undo_signal()

        # Should not update history counts or call apply
        history_scene.api.art.canvas.update_history.assert_not_called()
        history_scene._apply_layer_state.assert_not_called()

    def test_undo_pops_from_undo_pushes_to_redo(self, history_scene):
        """Test undo moves entry from undo to redo stack."""
        entry = {
            "type": "paint",
            "layer_id": 1,
            "before": {"image": b"before_data"},
            "after": {"image": b"after_data"},
        }
        history_scene.undo_history = [entry]

        history_scene.on_action_undo_signal()

        assert len(history_scene.undo_history) == 0
        assert len(history_scene.redo_history) == 1
        assert history_scene.redo_history[0] == entry

    def test_undo_applies_before_state(self, history_scene):
        """Test undo applies 'before' state from entry."""
        entry = {
            "type": "paint",
            "layer_id": 1,
            "before": {"image": b"before_data"},
            "after": {"image": b"after_data"},
        }
        history_scene.undo_history = [entry]

        history_scene.on_action_undo_signal()

        # Should apply the "before" state
        history_scene._apply_layer_state.assert_called_once_with(
            1, {"image": b"before_data"}
        )

    def test_undo_updates_history_counts(self, history_scene):
        """Test undo updates UI with new history counts."""
        entry = {"type": "paint", "layer_id": 1, "before": {}, "after": {}}
        history_scene.undo_history = [entry]

        history_scene.on_action_undo_signal()

        history_scene.api.art.canvas.update_history.assert_called_once_with(
            0, 1
        )

    def test_undo_calls_update_image_positions(self, history_scene):
        """Test undo refreshes image positions."""
        entry = {"type": "paint", "layer_id": 1, "before": {}, "after": {}}
        history_scene.undo_history = [entry]

        history_scene.on_action_undo_signal()

        mock_view = history_scene.views()[0]
        mock_view.updateImagePositions.assert_called_once()


class TestRedoFunctionality:
    """Test redo operation."""

    def test_redo_with_empty_history_does_nothing(self, history_scene):
        """Test redo with no redo entries."""
        assert len(history_scene.redo_history) == 0

        history_scene.on_action_redo_signal()

        history_scene.api.art.canvas.update_history.assert_not_called()
        history_scene._apply_layer_state.assert_not_called()

    def test_redo_pops_from_redo_pushes_to_undo(self, history_scene):
        """Test redo moves entry from redo to undo stack."""
        entry = {
            "type": "paint",
            "layer_id": 1,
            "before": {"image": b"before_data"},
            "after": {"image": b"after_data"},
        }
        history_scene.redo_history = [entry]

        history_scene.on_action_redo_signal()

        assert len(history_scene.redo_history) == 0
        assert len(history_scene.undo_history) == 1
        assert history_scene.undo_history[0] == entry

    def test_redo_applies_after_state(self, history_scene):
        """Test redo applies 'after' state from entry."""
        entry = {
            "type": "paint",
            "layer_id": 1,
            "before": {"image": b"before_data"},
            "after": {"image": b"after_data"},
        }
        history_scene.redo_history = [entry]

        history_scene.on_action_redo_signal()

        # Should apply the "after" state
        history_scene._apply_layer_state.assert_called_once_with(
            1, {"image": b"after_data"}
        )

    def test_redo_updates_memory_allocation(self, history_scene):
        """Test redo updates canvas memory allocation."""
        entry = {"type": "paint", "layer_id": 1, "before": {}, "after": {}}
        history_scene.redo_history = [entry]

        history_scene.on_action_redo_signal()

        history_scene._update_canvas_memory_allocation.assert_called_once()


class TestHistoryEntryApplication:
    """Test applying history entries."""

    def test_apply_layer_structure_entry(self, history_scene):
        """Test layer structure entries use special handler."""
        entry = {
            "type": "layer_create",
            "layer_id": 1,
            "before": {},
            "after": {},
        }

        history_scene._apply_history_entry(entry, "before")

        history_scene._apply_layer_structure.assert_called_once_with(
            entry, "before"
        )
        history_scene._apply_layer_state.assert_not_called()

    def test_apply_layer_delete_entry(self, history_scene):
        """Test layer delete uses structure handler."""
        entry = {
            "type": "layer_delete",
            "layer_id": 1,
            "before": {},
            "after": {},
        }

        history_scene._apply_history_entry(entry, "after")

        history_scene._apply_layer_structure.assert_called_once_with(
            entry, "after"
        )

    def test_apply_layer_reorder_entry(self, history_scene):
        """Test layer reorder uses structure handler."""
        entry = {
            "type": "layer_reorder",
            "layer_id": 1,
            "before": {},
            "after": {},
        }

        history_scene._apply_history_entry(entry, "before")

        history_scene._apply_layer_structure.assert_called_once_with(
            entry, "before"
        )

    def test_apply_paint_entry_with_state(self, history_scene):
        """Test paint entry applies layer state."""
        state_data = {"image": b"image_data", "x_pos": 100, "y_pos": 200}
        entry = {
            "type": "paint",
            "layer_id": 5,
            "before": state_data,
            "after": {},
        }

        history_scene._apply_history_entry(entry, "before")

        history_scene._apply_layer_state.assert_called_once_with(5, state_data)
        history_scene._refresh_layer_display.assert_called_once()

    def test_apply_entry_with_none_state_skips_apply(self, history_scene):
        """Test entry with None target state skips application."""
        entry = {
            "type": "paint",
            "layer_id": 1,
            "before": None,
            "after": {"image": b"data"},
        }

        history_scene._apply_history_entry(entry, "before")

        history_scene._apply_layer_state.assert_not_called()

    def test_apply_entry_updates_scene_and_views(self, history_scene):
        """Test apply entry updates scene and viewports."""
        entry = {
            "type": "paint",
            "layer_id": 1,
            "before": {"image": b"data"},
            "after": {},
        }

        history_scene._apply_history_entry(entry, "before")

        history_scene.update.assert_called_once()
        mock_view = history_scene.views()[0]
        mock_view.viewport().update.assert_called_once()
        mock_view.update.assert_called_once()


class TestStateCaptureHappyPath:
    """Test _capture_layer_state happy path."""

    def test_capture_none_layer_uses_global_settings(self, history_scene):
        """Test capturing state for None layer_id uses global settings."""
        history_scene.drawing_pad_settings.image = b"global_image"
        history_scene.drawing_pad_settings.mask = b"global_mask"
        history_scene.drawing_pad_settings.x_pos = 50
        history_scene.drawing_pad_settings.y_pos = 100
        history_scene.drawing_pad_settings.text_items = None
        history_scene._pending_image_binary = None
        history_scene._current_active_image_binary = None
        history_scene._get_current_selected_layer_id = MagicMock(
            return_value=None
        )

        state = history_scene._capture_layer_state(None)

        assert state["image"] == b"global_image"
        assert state["mask"] == b"global_mask"
        assert state["x_pos"] == 50
        assert state["y_pos"] == 100

    def test_capture_uses_pending_image_if_available(self, history_scene):
        """Test capture uses pending image binary if set."""
        history_scene._pending_image_binary = b"pending_data"
        history_scene._current_active_image_binary = b"active_data"
        history_scene.drawing_pad_settings.image = b"settings_data"
        history_scene._get_current_selected_layer_id = MagicMock(
            return_value=None
        )

        state = history_scene._capture_layer_state(None)

        # Should prefer pending over active/settings
        assert state["image"] == b"pending_data"

    def test_capture_uses_active_image_if_no_pending(self, history_scene):
        """Test capture uses active image if no pending."""
        history_scene._pending_image_binary = None
        history_scene._current_active_image_binary = b"active_data"
        history_scene.drawing_pad_settings.image = b"settings_data"
        history_scene._get_current_selected_layer_id = MagicMock(
            return_value=None
        )

        state = history_scene._capture_layer_state(None)

        assert state["image"] == b"active_data"

    def test_capture_uses_settings_image_if_no_pending_or_active(
        self, history_scene
    ):
        """Test capture falls back to settings image."""
        history_scene._pending_image_binary = None
        history_scene._current_active_image_binary = None
        history_scene.drawing_pad_settings.image = b"settings_data"
        history_scene._get_current_selected_layer_id = MagicMock(
            return_value=None
        )

        state = history_scene._capture_layer_state(None)

        assert state["image"] == b"settings_data"


class TestStateCaptureEdgeCases:
    """Test _capture_layer_state edge cases."""

    def test_capture_with_none_settings_returns_defaults(self, history_scene):
        """Test capture with missing settings returns safe defaults."""
        history_scene._get_layer_specific_settings = MagicMock(
            return_value=None
        )

        state = history_scene._capture_layer_state(layer_id=5)

        assert state["image"] is None
        assert state["mask"] is None
        assert state["x_pos"] == 0
        assert state["y_pos"] == 0

    def test_capture_handles_exception_getting_current_layer(
        self, history_scene
    ):
        """Test capture handles exception when getting current layer."""
        history_scene._get_current_selected_layer_id = MagicMock(
            side_effect=Exception("Layer error")
        )
        history_scene.drawing_pad_settings.image = b"image"

        # Should not raise, should still capture state
        state = history_scene._capture_layer_state(None)

        assert state["image"] == b"image"
