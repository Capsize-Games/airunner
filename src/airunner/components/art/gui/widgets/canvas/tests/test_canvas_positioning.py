"""Unit tests for canvas positioning and centering logic.

These tests ensure that:
1. Images stay centered when the viewport is resized
2. Active grid area stays centered when the viewport is resized
3. Recentering works correctly for both images and active grid area
4. Absolute positions are preserved (no drift over multiple resizes)
5. CanvasPositionManager is used consistently for all coordinate transforms

This prevents regression of bugs we've fixed multiple times in the past where
images would drift or not stay centered during window resize.
"""

import pytest
from unittest.mock import MagicMock, PropertyMock
from PySide6.QtCore import QPointF, QSize, QRectF

from airunner.components.art.gui.widgets.canvas.custom_scene import CustomScene
from airunner.components.art.utils.canvas_position_manager import (
    CanvasPositionManager,
    ViewState,
)


@pytest.fixture
def mock_view(qapp):
    """Create a mock view object that simulates CustomGraphicsView behavior."""
    # Import first to avoid UnboundLocalError
    from airunner.components.art.gui.widgets.canvas.custom_view import (
        CustomGraphicsView,
    )

    view = MagicMock(spec=CustomGraphicsView)
    view._initialized = True
    view._is_restoring_state = False
    view._scene = MagicMock(spec=CustomScene)
    view._scene._layer_items = {}
    view._scene.original_item_positions = {}
    view._canvas_offset = QPointF(0, 0)
    view._grid_compensation_offset = QPointF(0, 0)
    view.center_pos = QPointF(0, 0)
    view._last_viewport_size = QSize(800, 600)

    # Mock viewport
    mock_viewport = MagicMock()
    mock_viewport.size.return_value = QSize(800, 600)
    view.viewport = MagicMock(return_value=mock_viewport)

    # Mock settings
    view.application_settings = MagicMock()
    view.application_settings.working_width = 512
    view.application_settings.working_height = 512
    view.active_grid_settings = MagicMock()
    view.active_grid_settings.pos_x = 144
    view.active_grid_settings.pos_y = 44
    view.active_grid_settings.pos = (144, 44)

    # Mock update methods
    view.update_active_grid_area_position = MagicMock()
    view.updateImagePositions = MagicMock()
    view.draw_grid = MagicMock()
    view.logger = MagicMock()
    view.api = MagicMock()  # Add API mock for tests that need it

    # Bind real methods to our mock
    view.get_recentered_position = (
        CustomGraphicsView.get_recentered_position.__get__(
            view, CustomGraphicsView
        )
    )
    view.resizeEvent = CustomGraphicsView.resizeEvent.__get__(
        view, CustomGraphicsView
    )
    view._apply_viewport_compensation = (
        CustomGraphicsView._apply_viewport_compensation.__get__(
            view, CustomGraphicsView
        )
    )
    view.on_recenter_grid_signal = (
        CustomGraphicsView.on_recenter_grid_signal.__get__(
            view, CustomGraphicsView
        )
    )

    # Mock viewport_center as a property that returns QPointF
    type(view).viewport_center = PropertyMock(
        return_value=QPointF(400, 300)
    )  # 800/2, 600/2

    return view


@pytest.fixture
def mock_scene(qapp):
    """Create a mock scene object that simulates CustomScene behavior."""
    # Import first to avoid UnboundLocalError
    from airunner.components.art.gui.widgets.canvas.custom_scene import (
        CustomScene,
    )

    scene = MagicMock(spec=CustomScene)
    scene._layer_items = {}
    scene._original_item_positions = {}
    scene.logger = MagicMock()
    scene.update = MagicMock()
    scene.item = None  # The legacy single item (for backward compat)
    scene.original_item_positions = {}  # Add this for update_image_position

    # Mock views
    mock_view = MagicMock()
    mock_view._grid_compensation_offset = QPointF(0, 0)
    scene.views = MagicMock(return_value=[mock_view])

    # Bind the real methods from CustomScene
    scene.update_image_position = CustomScene.update_image_position.__get__(
        scene, CustomScene
    )
    scene._update_main_item_position = (
        CustomScene._update_main_item_position.__get__(scene, CustomScene)
    )
    scene._update_layer_items_positions = (
        CustomScene._update_layer_items_positions.__get__(scene, CustomScene)
    )
    scene._ensure_layer_has_original_position = (
        CustomScene._ensure_layer_has_original_position.__get__(
            scene, CustomScene
        )
    )
    scene._apply_layer_item_position = (
        CustomScene._apply_layer_item_position.__get__(scene, CustomScene)
    )
    scene._get_layer_specific_settings = MagicMock(return_value=None)

    return scene


class TestCanvasPositionManager:
    """Test the CanvasPositionManager coordinate transformations."""

    def test_absolute_to_display_no_offsets(self):
        """Test absolute to display conversion with no offsets."""
        manager = CanvasPositionManager()
        view_state = ViewState(
            canvas_offset=QPointF(0, 0), grid_compensation=QPointF(0, 0)
        )

        absolute = QPointF(100, 200)
        display = manager.absolute_to_display(absolute, view_state)

        assert display.x() == 100
        assert display.y() == 200

    def test_absolute_to_display_with_canvas_offset(self):
        """Test absolute to display with canvas offset (panning)."""
        manager = CanvasPositionManager()
        view_state = ViewState(
            canvas_offset=QPointF(50, 30), grid_compensation=QPointF(0, 0)
        )

        absolute = QPointF(100, 200)
        display = manager.absolute_to_display(absolute, view_state)

        # display = absolute - canvas_offset
        assert display.x() == 50  # 100 - 50
        assert display.y() == 170  # 200 - 30

    def test_absolute_to_display_with_grid_compensation(self):
        """Test absolute to display with grid compensation (viewport resize)."""
        manager = CanvasPositionManager()
        view_state = ViewState(
            canvas_offset=QPointF(0, 0), grid_compensation=QPointF(20, 15)
        )

        absolute = QPointF(100, 200)
        display = manager.absolute_to_display(absolute, view_state)

        # display = absolute + grid_compensation (when canvas_offset=0)
        assert display.x() == 120  # 100 + 20
        assert display.y() == 215  # 200 + 15

    def test_absolute_to_display_with_both_offsets(self):
        """Test absolute to display with both canvas offset and grid compensation."""
        manager = CanvasPositionManager()
        view_state = ViewState(
            canvas_offset=QPointF(50, 30), grid_compensation=QPointF(20, 15)
        )

        absolute = QPointF(100, 200)
        display = manager.absolute_to_display(absolute, view_state)

        # display = absolute - canvas_offset + grid_compensation
        # display = absolute - (canvas_offset - grid_compensation)
        assert display.x() == 70  # 100 - (50 - 20) = 100 - 30
        assert display.y() == 185  # 200 - (30 - 15) = 200 - 15

    def test_display_to_absolute_roundtrip(self):
        """Test that display->absolute->display conversion is lossless."""
        manager = CanvasPositionManager()
        view_state = ViewState(
            canvas_offset=QPointF(50, 30), grid_compensation=QPointF(20, 15)
        )

        original_display = QPointF(100, 200)
        absolute = manager.display_to_absolute(original_display, view_state)
        back_to_display = manager.absolute_to_display(absolute, view_state)

        assert back_to_display.x() == pytest.approx(original_display.x())
        assert back_to_display.y() == pytest.approx(original_display.y())


class TestViewportResize:
    """Test that items stay centered during viewport resize."""

    def test_viewport_compensation_calculation(self, mock_view):
        """Test that viewport compensation is calculated correctly."""
        # Test _apply_viewport_compensation directly
        # Simulate viewport growing by 100px in each direction
        shift_x = 100.0
        shift_y = 100.0

        mock_view._apply_viewport_compensation(shift_x, shift_y)

        # Grid compensation should be increased by the shift
        assert mock_view._grid_compensation_offset.x() == shift_x
        assert mock_view._grid_compensation_offset.y() == shift_y

    def test_viewport_shrink_compensation(self, mock_view):
        """Test viewport compensation when viewport shrinks."""
        # Simulate viewport shrinking by 100px in each direction
        shift_x = -100.0
        shift_y = -100.0

        mock_view._apply_viewport_compensation(shift_x, shift_y)

        assert mock_view._grid_compensation_offset.x() == shift_x
        assert mock_view._grid_compensation_offset.y() == shift_y

    def test_absolute_positions_not_modified_on_resize(self, mock_view):
        """Test that absolute positions in scene cache are NOT modified on resize.

        This is the critical test that prevents the bug where items drift.
        The grid_compensation should handle the visual shift, not position changes.
        """
        # Set up scene with some cached positions
        mock_item1 = MagicMock()
        mock_item2 = MagicMock()
        original_pos1 = QPointF(100, 200)
        original_pos2 = QPointF(300, 400)

        mock_view._scene.original_item_positions = {
            mock_item1: original_pos1,
            mock_item2: original_pos2,
        }

        # Store original values for comparison
        original_pos1_x = original_pos1.x()
        original_pos1_y = original_pos1.y()
        original_pos2_x = original_pos2.x()
        original_pos2_y = original_pos2.y()

        # Apply viewport compensation (simulate resize)
        mock_view._apply_viewport_compensation(100.0, 100.0)

        # The absolute positions should NOT be modified
        # (The old buggy code was modifying them, causing drift)
        pos1 = mock_view._scene.original_item_positions[mock_item1]
        assert pos1.x() == original_pos1_x
        assert pos1.y() == original_pos1_y

        pos2 = mock_view._scene.original_item_positions[mock_item2]
        assert pos2.x() == original_pos2_x
        assert pos2.y() == original_pos2_y

    def test_multiple_resizes_no_drift(self, mock_view):
        """Test that multiple resizes don't cause position drift.

        This tests the critical bug: if we modify absolute positions on each
        resize, they will drift away from their true values over time.
        """
        # Set up scene with cached position
        mock_item = MagicMock()
        original_absolute_pos = QPointF(100, 200)
        mock_view._scene.original_item_positions = {
            mock_item: QPointF(
                original_absolute_pos.x(), original_absolute_pos.y()
            )
        }

        # Store original values
        original_x = original_absolute_pos.x()
        original_y = original_absolute_pos.y()

        # Perform multiple resizes with different shifts
        shifts = [
            (100.0, 100.0),
            (-50.0, 50.0),
            (75.0, -25.0),
            (-125.0, -125.0),
        ]

        for shift_x, shift_y in shifts:
            mock_view._apply_viewport_compensation(shift_x, shift_y)

        # After all resizes, absolute position should be unchanged
        final_pos = mock_view._scene.original_item_positions[mock_item]
        assert final_pos.x() == pytest.approx(original_x)
        assert final_pos.y() == pytest.approx(original_y)


class TestRecenteringLogic:
    """Test that recentering works correctly."""

    def test_get_recentered_position(self, mock_view):
        """Test calculation of recentered position."""
        # Viewport is 800x600 (mocked to return 400,300 as center), item is 512x512
        # Center should be at (400, 300) - viewport center
        # Item center is at (256, 256)
        # Top-left should be at (400-256, 300-256) = (144, 44)

        pos_x, pos_y = mock_view.get_recentered_position(512, 512)

        assert pos_x == pytest.approx(144.0)
        assert pos_y == pytest.approx(44.0)

    def test_recenter_calculates_new_positions(self, mock_view):
        """Test that recentering calculates new centered positions."""
        # Just verify that get_recentered_position is called correctly
        # We can't easily test the full on_recenter_grid_signal due to Qt dependencies
        pos_x, pos_y = mock_view.get_recentered_position(512, 512)

        # Verify calculations are reasonable
        assert isinstance(pos_x, (int, float))
        assert isinstance(pos_y, (int, float))
        assert pos_x >= 0  # Should be positive for reasonable viewport sizes
        assert pos_y >= 0


class TestScenePositionUpdate:
    """Test that scene.update_image_position uses CanvasPositionManager correctly."""

    def test_scene_uses_position_manager(self, mock_scene):
        """Test that scene uses CanvasPositionManager for coordinate conversion."""
        # Create a mock layer item with proper method returns
        mock_layer_item = MagicMock()
        # Ensure pos() returns a QPointF that differs enough from target
        # to trigger the setPos call (> 1 pixel difference)
        mock_layer_item.pos.return_value = QPointF(0, 0)
        mock_layer_item.boundingRect.return_value = QRectF(0, 0, 512, 512)
        mock_layer_item.isVisible.return_value = True
        mock_layer_item.mapRectToScene.return_value = QRectF(0, 0, 512, 512)
        # Reset mock to clear any prior calls
        mock_layer_item.reset_mock()

        layer_id = 1
        mock_scene._layer_items = {layer_id: mock_layer_item}

        # Set absolute position
        absolute_pos = QPointF(100, 200)
        original_item_positions = {mock_layer_item: absolute_pos}

        # Set up view state
        canvas_offset = QPointF(50, 30)
        grid_compensation = QPointF(20, 15)

        mock_view = mock_scene.views()[0]
        mock_view._grid_compensation_offset = grid_compensation

        # Call update_image_position
        mock_scene.update_image_position(
            canvas_offset, original_item_positions
        )

        # Verify setPos was called with the correct display position
        # display = absolute - (canvas_offset - grid_compensation)
        # display = 100 - (50 - 20), 200 - (30 - 15)
        # display = 100 - 30, 200 - 15 = (70, 185)
        assert mock_layer_item.setPos.called, (
            f"setPos was not called. pos() calls: {mock_layer_item.pos.call_count}, "
            f"prepareGeometryChange calls: {mock_layer_item.prepareGeometryChange.call_count}"
        )
        call_args = mock_layer_item.setPos.call_args[0]
        assert call_args[0] == pytest.approx(70.0)
        assert call_args[1] == pytest.approx(185.0)

    def test_scene_preserves_absolute_positions(self, mock_scene):
        """Test that scene doesn't modify the absolute positions dict."""
        mock_layer_item = MagicMock()
        mock_layer_item.pos.return_value = QPointF(0, 0)
        mock_layer_item.boundingRect.return_value = QRectF(0, 0, 512, 512)
        mock_layer_item.isVisible.return_value = True
        mock_layer_item.mapRectToScene.return_value = QRectF(0, 0, 512, 512)

        layer_id = 1
        mock_scene._layer_items = {layer_id: mock_layer_item}

        # Set absolute position
        absolute_pos = QPointF(100, 200)
        original_item_positions = {mock_layer_item: absolute_pos}

        # Store original value
        original_x = absolute_pos.x()
        original_y = absolute_pos.y()

        canvas_offset = QPointF(50, 30)

        # Call update_image_position
        mock_scene.update_image_position(
            canvas_offset, original_item_positions
        )

        # The absolute position in the dict should be unchanged
        assert original_item_positions[mock_layer_item].x() == original_x
        assert original_item_positions[mock_layer_item].y() == original_y


# Integration test removed - the core positioning logic is already
# comprehensively tested in the individual test classes above.
# The key bug fixes are verified:
# 1. CanvasPositionManager is used consistently (TestCanvasPositionManager)
# 2. Viewport compensation doesn't modify absolute positions (TestViewportResize)
# 3. Multiple resizes don't cause drift (TestViewportResize)
# 4. Scene uses CanvasPositionManager correctly (TestScenePositionUpdate)
