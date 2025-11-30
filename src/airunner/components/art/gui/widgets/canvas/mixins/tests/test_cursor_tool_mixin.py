"""Unit tests for CursorToolMixin.

Tests cursor caching, tool management, and drag mode functionality.
"""

import pytest
from unittest.mock import Mock, patch
from PySide6.QtWidgets import QGraphicsView

from airunner.components.art.gui.widgets.canvas.mixins.cursor_tool_mixin import (
    CursorToolMixin,
)
from airunner.enums import CanvasToolName


class MockView(CursorToolMixin, QGraphicsView):
    """Test class combining mixin with QGraphicsView."""

    def __init__(self):
        # Mock Qt module for cursor access
        self.Qt = Mock()
        self.Qt.GlobalColor.white = Mock()
        self.Qt.GlobalColor.transparent = Mock()

        # Mock application settings
        self.application_settings = Mock()
        self.application_settings.current_tool = None

        # Mock methods that mixin calls
        self._set_text_items_interaction = Mock()
        self._update_active_grid_mouse_acceptance = Mock()

        super().__init__()


@pytest.fixture
def mock_view(qapp):
    """Create a mock view with CursorToolMixin."""
    return MockView()


class TestCursorToolMixinInit:
    """Test mixin initialization."""

    def test_init_creates_cursor_cache(self, mock_view):
        """Test that __init__ creates empty cursor cache."""
        assert hasattr(mock_view, "_cursor_cache")
        assert isinstance(mock_view._cursor_cache, dict)
        assert len(mock_view._cursor_cache) == 0

    def test_init_creates_current_cursor(self, mock_view):
        """Test that __init__ creates current_cursor attribute."""
        assert hasattr(mock_view, "_current_cursor")
        assert mock_view._current_cursor is None


class TestCurrentToolProperty:
    """Test current_tool property."""

    def test_current_tool_none(self, mock_view):
        """Test current_tool returns None when no tool set."""
        mock_view.application_settings.current_tool = None
        assert mock_view.current_tool is None

    def test_current_tool_with_valid_value(self, mock_view):
        """Test current_tool returns enum value for valid tool."""
        mock_view.application_settings.current_tool = "brush"
        assert mock_view.current_tool == CanvasToolName.BRUSH

    def test_current_tool_with_enum_value(self, mock_view):
        """Test current_tool handles enum value."""
        mock_view.application_settings.current_tool = CanvasToolName.ERASER
        assert mock_view.current_tool == CanvasToolName.ERASER

    def test_current_tool_with_invalid_value(self, mock_view):
        """Test current_tool returns None for invalid value."""
        mock_view.application_settings.current_tool = "invalid_tool"
        assert mock_view.current_tool is None

    def test_current_tool_without_settings_attribute(self, mock_view):
        """Test current_tool handles missing application_settings."""
        # Mock with object that raises AttributeError
        mock_view.application_settings = Mock()
        del mock_view.application_settings.current_tool
        # Should return None when attribute doesn't exist
        result = mock_view.current_tool
        assert result is None


class TestGetCachedCursor:
    """Test get_cached_cursor method."""

    @patch(
        "airunner.components.art.gui.widgets.canvas.mixins.cursor_tool_mixin.circle_cursor"
    )
    def test_get_cached_cursor_creates_new_brush(
        self, mock_circle_cursor, mock_view
    ):
        """Test creating new cursor for brush tool."""
        mock_cursor = Mock()
        mock_circle_cursor.return_value = mock_cursor

        result = mock_view.get_cached_cursor(CanvasToolName.BRUSH, 10)

        assert result == mock_cursor
        assert (CanvasToolName.BRUSH, 10) in mock_view._cursor_cache
        mock_circle_cursor.assert_called_once()

    @patch(
        "airunner.components.art.gui.widgets.canvas.mixins.cursor_tool_mixin.circle_cursor"
    )
    def test_get_cached_cursor_creates_new_eraser(
        self, mock_circle_cursor, mock_view
    ):
        """Test creating new cursor for eraser tool."""
        mock_cursor = Mock()
        mock_circle_cursor.return_value = mock_cursor

        result = mock_view.get_cached_cursor(CanvasToolName.ERASER, 15)

        assert result == mock_cursor
        assert (CanvasToolName.ERASER, 15) in mock_view._cursor_cache

    @patch(
        "airunner.components.art.gui.widgets.canvas.mixins.cursor_tool_mixin.circle_cursor"
    )
    def test_get_cached_cursor_returns_cached(
        self, mock_circle_cursor, mock_view
    ):
        """Test that cached cursor is returned without creating new one."""
        mock_cursor = Mock()
        mock_view._cursor_cache[(CanvasToolName.BRUSH, 20)] = mock_cursor

        result = mock_view.get_cached_cursor(CanvasToolName.BRUSH, 20)

        assert result == mock_cursor
        mock_circle_cursor.assert_not_called()

    def test_get_cached_cursor_non_custom_tool(self, mock_view):
        """Test that non-custom tools return None."""
        result = mock_view.get_cached_cursor(CanvasToolName.MOVE, 10)
        assert result is None
        assert (CanvasToolName.MOVE, 10) not in mock_view._cursor_cache

    @patch(
        "airunner.components.art.gui.widgets.canvas.mixins.cursor_tool_mixin.circle_cursor"
    )
    def test_get_cached_cursor_different_sizes(
        self, mock_circle_cursor, mock_view
    ):
        """Test that different sizes create separate cache entries."""
        mock_cursor_10 = Mock()
        mock_cursor_20 = Mock()
        mock_circle_cursor.side_effect = [mock_cursor_10, mock_cursor_20]

        result1 = mock_view.get_cached_cursor(CanvasToolName.BRUSH, 10)
        result2 = mock_view.get_cached_cursor(CanvasToolName.BRUSH, 20)

        assert result1 == mock_cursor_10
        assert result2 == mock_cursor_20
        assert len(mock_view._cursor_cache) == 2


class TestToggleDragMode:
    """Test toggle_drag_mode method."""

    def test_toggle_drag_mode_sets_no_drag(self, mock_view):
        """Test that toggle_drag_mode sets drag mode to NoDrag."""
        mock_view.toggle_drag_mode()
        assert mock_view.dragMode() == QGraphicsView.DragMode.NoDrag


class TestOnToolChangedSignal:
    """Test on_tool_changed_signal method."""

    def test_on_tool_changed_calls_toggle_drag_mode(self, mock_view):
        """Test that tool change calls toggle_drag_mode."""
        with patch.object(mock_view, "toggle_drag_mode") as mock_toggle:
            mock_view.on_tool_changed_signal({})
            mock_toggle.assert_called_once()

    def test_on_tool_changed_updates_text_interaction_other_tool(
        self, mock_view
    ):
        """Test text interaction disabled for non-TEXT tool."""
        mock_view.application_settings.current_tool = CanvasToolName.BRUSH

        mock_view.on_tool_changed_signal({})

        mock_view._set_text_items_interaction.assert_called_once_with(False)

    def test_on_tool_changed_calls_update_grid_acceptance(self, mock_view):
        """Test that tool change updates active grid mouse acceptance."""
        mock_view.on_tool_changed_signal({})

        mock_view._update_active_grid_mouse_acceptance.assert_called_once()

    def test_on_tool_changed_handles_exception_in_grid_update(self, mock_view):
        """Test that exceptions in grid update are caught."""
        mock_view._update_active_grid_mouse_acceptance.side_effect = Exception(
            "Test error"
        )

        # Should not raise exception
        mock_view.on_tool_changed_signal({})


class TestCursorCachePerformance:
    """Test cursor cache performance characteristics."""

    @patch(
        "airunner.components.art.gui.widgets.canvas.mixins.cursor_tool_mixin.circle_cursor"
    )
    def test_multiple_calls_same_params_use_cache(
        self, mock_circle_cursor, mock_view
    ):
        """Test that multiple calls with same params only create cursor once."""
        mock_cursor = Mock()
        mock_circle_cursor.return_value = mock_cursor

        # Call 100 times with same parameters
        for _ in range(100):
            result = mock_view.get_cached_cursor(CanvasToolName.BRUSH, 10)
            assert result == mock_cursor

        # circle_cursor should only be called once
        assert mock_circle_cursor.call_count == 1

    @patch(
        "airunner.components.art.gui.widgets.canvas.mixins.cursor_tool_mixin.circle_cursor"
    )
    def test_cache_stores_different_tool_size_combinations(
        self, mock_circle_cursor, mock_view
    ):
        """Test cache correctly stores different combinations."""
        cursors = []
        for i in range(5):
            cursor = Mock()
            cursors.append(cursor)
        mock_circle_cursor.side_effect = cursors

        # Create 5 different combinations
        combinations = [
            (CanvasToolName.BRUSH, 10),
            (CanvasToolName.BRUSH, 20),
            (CanvasToolName.ERASER, 10),
            (CanvasToolName.ERASER, 20),
            (CanvasToolName.BRUSH, 30),
        ]

        for tool, size in combinations:
            mock_view.get_cached_cursor(tool, size)

        # All should be in cache
        assert len(mock_view._cursor_cache) == 5

        # Verify each combination returns correct cursor
        for i, (tool, size) in enumerate(combinations):
            assert mock_view._cursor_cache[(tool, size)] == cursors[i]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
