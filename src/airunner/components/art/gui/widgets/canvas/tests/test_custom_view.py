"""
Unit tests for CustomGraphicsView.

Tests focus on:
- Property getters and setters
- Canvas offset management
- Scene initialization
- Tool handling
- Grid area display
- Viewport events
- Cursor management
"""

import types
from unittest.mock import Mock, patch
from PySide6.QtCore import QPointF, QSize
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QGraphicsView
import pytest

from airunner.components.art.gui.widgets.canvas.custom_view import (
    CustomGraphicsView,
)
from airunner.enums import CanvasToolName


@pytest.fixture
def mock_settings():
    """Create mock settings objects."""
    active_grid = Mock()
    active_grid.pos_x = 0
    active_grid.pos_y = 0
    active_grid.pos = (0, 0)

    grid = Mock()
    grid.show_grid = True
    grid.canvas_color = "#000000"

    app_settings = Mock()
    app_settings.working_width = 512
    app_settings.working_height = 512
    app_settings.current_tool = None

    return active_grid, grid, app_settings


@pytest.fixture
def custom_view(qapp, mock_settings):
    """Create a CustomGraphicsView instance with mocked settings."""
    view = CustomGraphicsView()
    active, grid, app_settings = mock_settings

    def fake_get_or_cache_settings(self, cls, eager_load=None):
        name = getattr(cls, "__name__", str(cls))
        if name == "ActiveGridSettings":
            return active
        if name == "GridSettings":
            return grid
        if name == "ApplicationSettings":
            return app_settings
        return cls()

    view._get_or_cache_settings = types.MethodType(
        fake_get_or_cache_settings, view
    )
    view.setProperty("canvas_type", "image")

    return view


class TestProperties:
    """Test property getters and setters."""

    def test_canvas_offset_getter(self, custom_view):
        """Test canvas_offset property getter."""
        custom_view._canvas_offset = QPointF(10, 20)
        assert custom_view.canvas_offset == QPointF(10, 20)

    def test_canvas_offset_setter(self, custom_view):
        """Test canvas_offset property setter."""
        custom_view.canvas_offset = QPointF(30, 40)
        assert custom_view._canvas_offset == QPointF(30, 40)

    def test_canvas_offset_x(self, custom_view):
        """Test canvas_offset_x property."""
        custom_view.canvas_offset = QPointF(15, 25)
        assert custom_view.canvas_offset_x == 15.0

    def test_canvas_offset_y(self, custom_view):
        """Test canvas_offset_y property."""
        custom_view.canvas_offset = QPointF(15, 25)
        assert custom_view.canvas_offset_y == 25.0

    def test_zero_point(self, custom_view):
        """Test zero_point property returns QPointF(0, 0)."""
        assert custom_view.zero_point == QPointF(0, 0)

    def test_grid_compensation_offset(self, custom_view):
        """Test grid_compensation_offset property."""
        custom_view._grid_compensation_offset = QPointF(5, 10)
        assert custom_view.grid_compensation_offset == QPointF(5, 10)

    def test_viewport_center(self, custom_view):
        """Test viewport_center property calculates correctly."""
        # Mock viewport size
        with patch.object(custom_view, "viewport") as mock_viewport:
            mock_viewport.return_value.size.return_value = QSize(800, 600)
            center = custom_view.viewport_center
            assert center == QPointF(400, 300)

    def test_canvas_type_property(self, custom_view):
        """Test canvas_type property returns set value."""
        assert custom_view.canvas_type == "image"


class TestSceneInitialization:
    """Test scene creation and initialization."""

    def test_scene_property_creates_image_scene(self, custom_view):
        """Test that accessing scene property creates CustomScene for image canvas."""
        scene = custom_view.scene
        assert scene is not None
        assert scene.parent == custom_view
        assert custom_view._scene is scene

    def test_scene_property_returns_existing(self, custom_view):
        """Test that scene property returns existing scene."""
        scene1 = custom_view.scene
        scene2 = custom_view.scene
        assert scene1 is scene2

    def test_scene_setter(self, custom_view):
        """Test scene property setter."""
        mock_scene = Mock()
        custom_view.scene = mock_scene
        assert custom_view._scene is mock_scene


class TestCanvasOffsetManagement:
    """Test loading and saving canvas offset."""

    def test_load_canvas_offset(self, custom_view):
        """Test loading canvas offset from QSettings."""
        custom_view.settings.value = Mock(
            side_effect=lambda key, default: {
                "canvas_offset_x": 100.0,
                "canvas_offset_y": 200.0,
                "center_pos_x": 50.0,
                "center_pos_y": 75.0,
            }.get(key, default)
        )

        custom_view.load_canvas_offset()

        assert custom_view.canvas_offset == QPointF(100.0, 200.0)
        assert custom_view.center_pos == QPointF(50.0, 75.0)

    def test_load_canvas_offset_with_defaults(self, custom_view):
        """Test loading canvas offset when no values exist."""
        custom_view.settings.value = Mock(return_value=None)

        custom_view.load_canvas_offset()

        # Should default to 0, 0
        assert custom_view.canvas_offset == QPointF(0.0, 0.0)

    def test_save_canvas_offset(self, custom_view):
        """Test saving canvas offset to QSettings."""
        custom_view.canvas_offset = QPointF(150.0, 250.0)
        custom_view.center_pos = QPointF(60.0, 80.0)
        custom_view.settings.setValue = Mock()

        custom_view.save_canvas_offset()

        # Verify setValue was called with correct values
        calls = custom_view.settings.setValue.call_args_list
        assert any(
            args[0][0] == "canvas_offset_x" and args[0][1] == 150.0
            for args in calls
        )
        assert any(
            args[0][0] == "canvas_offset_y" and args[0][1] == 250.0
            for args in calls
        )


class TestToolHandling:
    """Test tool-related functionality."""

    def test_current_tool_property_none(self, custom_view):
        """Test current_tool property when tool is None."""
        assert custom_view.current_tool is None

    def test_current_tool_property_with_value(
        self, custom_view, mock_settings
    ):
        """Test current_tool property with a valid tool."""
        _, _, app_settings = mock_settings
        app_settings.current_tool = "brush"
        assert custom_view.current_tool == CanvasToolName.BRUSH

    def test_toggle_drag_mode(self, custom_view):
        """Test toggle_drag_mode sets drag mode to NoDrag."""
        custom_view.toggle_drag_mode()
        assert custom_view.dragMode() == QGraphicsView.DragMode.NoDrag


class TestGetRecenteredPosition:
    """Test get_recentered_position method."""

    def test_get_recentered_position(self, custom_view):
        """Test calculating recentered position."""
        # Mock viewport() to return a mock with size() that returns QSize(800, 600)
        mock_viewport = Mock()
        mock_viewport.size.return_value = QSize(800, 600)
        with patch.object(custom_view, "viewport", return_value=mock_viewport):
            x, y = custom_view.get_recentered_position(256, 256)
            # Should center the item (viewport center is 400, 300)
            assert x == 400 - 128  # viewport_center_x - item_center_x
            assert y == 300 - 128  # viewport_center_y - item_center_y


class TestSceneManagement:
    """Test scene manipulation methods."""

    def test_set_scene_rect(self, custom_view):
        """Test setting scene rect to viewport size."""
        _ = custom_view.scene  # Ensure scene exists
        with patch.object(custom_view, "viewport") as mock_viewport:
            mock_viewport.return_value.size.return_value = QSize(800, 600)
            custom_view.set_scene_rect()
            scene_rect = custom_view.scene.sceneRect()
            assert scene_rect.width() == 800
            assert scene_rect.height() == 600

    def test_update_scene(self, custom_view):
        """Test update_scene calls scene.update()."""
        _ = custom_view.scene
        with patch.object(custom_view.scene, "update") as mock_update:
            custom_view.update_scene()
            mock_update.assert_called_once()

    def test_remove_scene_item_none(self, custom_view):
        """Test remove_scene_item with None item."""
        # Should not raise an exception
        custom_view.remove_scene_item(None)

    def test_remove_scene_item_valid(self, custom_view):
        """Test removing a valid scene item."""
        _ = custom_view.scene
        mock_item = Mock()
        mock_item.scene.return_value = custom_view.scene

        with patch.object(custom_view.scene, "removeItem") as mock_remove:
            custom_view.remove_scene_item(mock_item)
            mock_remove.assert_called_once_with(mock_item)


class TestGridDrawing:
    """Test grid drawing functionality."""

    def test_clear_lines_removes_grid(self, custom_view):
        """Test clear_lines removes grid item."""
        _ = custom_view.scene
        mock_grid = Mock()
        custom_view.grid_item = mock_grid

        with patch.object(custom_view.scene, "removeItem") as mock_remove:
            custom_view.clear_lines()
            mock_remove.assert_called_once_with(mock_grid)
            assert custom_view.grid_item is None

    def test_clear_lines_when_none(self, custom_view):
        """Test clear_lines when grid_item is None."""
        custom_view.grid_item = None
        custom_view.clear_lines()  # Should not raise an exception


class TestViewportEvents:
    """Test viewport resize and show events."""

    def test_resize_event_during_restoration(self, custom_view):
        """Test resizeEvent skips compensation during restoration."""
        custom_view._is_restoring_state = True
        custom_view._initialized = False
        old_size = QSize(800, 600)
        new_size = QSize(1000, 700)
        custom_view._last_viewport_size = old_size

        event = QResizeEvent(new_size, old_size)
        custom_view.resizeEvent(event)

        # Should update tracked size to actual viewport size (not event size in test)
        # In mixin, it uses self.viewport().size() which returns actual viewport dimensions
        assert custom_view._last_viewport_size == custom_view.viewport().size()

    def test_resize_event_same_size(self, custom_view):
        """Test resizeEvent with no size change."""
        custom_view._is_restoring_state = False
        custom_view._initialized = True
        size = QSize(800, 600)
        custom_view._last_viewport_size = size

        event = QResizeEvent(size, size)
        custom_view.resizeEvent(event)

        # Should return early without changes


class TestCursorManagement:
    """Test cursor caching and updates."""

    def test_get_cached_cursor_creates_new(self, custom_view):
        """Test get_cached_cursor creates cursor if not cached."""
        with patch(
            "airunner.components.art.gui.widgets.canvas.mixins.cursor_tool_mixin.circle_cursor"
        ) as mock_circle:
            mock_cursor = Mock()
            mock_circle.return_value = mock_cursor

            result = custom_view.get_cached_cursor(CanvasToolName.BRUSH, 10)

            assert result == mock_cursor
            assert (CanvasToolName.BRUSH, 10) in custom_view._cursor_cache

    def test_get_cached_cursor_returns_cached(self, custom_view):
        """Test get_cached_cursor returns cached cursor."""
        mock_cursor = Mock()
        custom_view._cursor_cache[(CanvasToolName.ERASER, 15)] = mock_cursor

        result = custom_view.get_cached_cursor(CanvasToolName.ERASER, 15)

        assert result == mock_cursor


class TestSignalHandlers:
    """Test signal handler methods."""

    def test_on_main_window_loaded_signal(self, custom_view):
        """Test on_main_window_loaded_signal sets initialized flag."""
        custom_view.initialized = False
        with patch.object(custom_view, "do_draw"):
            custom_view.on_main_window_loaded_signal()
            assert custom_view.initialized is True

    def test_on_canvas_do_draw_signal(self, custom_view):
        """Test on_canvas_do_draw_signal calls do_draw."""
        with patch.object(custom_view, "do_draw") as mock_draw:
            custom_view.on_canvas_do_draw_signal({"force_draw": True})
            mock_draw.assert_called_once_with(force_draw=True)

    def test_on_zoom_level_changed_signal(self, custom_view):
        """Test on_zoom_level_changed_signal updates transform."""
        mock_transform = Mock()
        custom_view.zoom_handler.on_zoom_level_changed = Mock(
            return_value=mock_transform
        )

        with patch.object(custom_view, "setTransform") as mock_set:
            with patch.object(custom_view, "do_draw"):
                custom_view.on_zoom_level_changed_signal()
                mock_set.assert_called_once_with(mock_transform)


class TestCanvasColorManagement:
    """Test canvas color setting."""

    def test_set_canvas_color_default(self, custom_view):
        """Test set_canvas_color with default values."""
        _ = custom_view.scene
        custom_view.set_canvas_color()

        # Verify background brush was set
        assert custom_view.current_background_color is not None

    def test_set_canvas_color_custom(self, custom_view):
        """Test set_canvas_color with custom color."""
        _ = custom_view.scene
        custom_view.set_canvas_color(canvas_color="#FF0000")

        assert custom_view.current_background_color == "#FF0000"


class TestPanUpdateTimer:
    """Test pan update timer functionality."""

    def test_do_pan_update(self, custom_view):
        """Test _do_pan_update calls position update methods."""
        _ = custom_view.scene
        with patch.object(
            custom_view, "update_active_grid_area_position"
        ) as mock_grid:
            with patch.object(
                custom_view, "updateImagePositions"
            ) as mock_images:
                with patch.object(custom_view, "draw_grid") as mock_draw:
                    custom_view._do_pan_update()

                    mock_grid.assert_called_once()
                    mock_images.assert_called_once()
                    mock_draw.assert_called_once()

    def test_do_pan_update_with_pending_event(self, custom_view):
        """Test _do_pan_update handles pending events."""
        custom_view._pending_pan_event = True
        with patch.object(custom_view, "update_active_grid_area_position"):
            with patch.object(custom_view, "updateImagePositions"):
                with patch.object(custom_view, "draw_grid"):
                    with patch.object(
                        custom_view._pan_update_timer, "start"
                    ) as mock_start:
                        custom_view._do_pan_update()
                        assert custom_view._pending_pan_event is False
                        mock_start.assert_called_once_with(1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
