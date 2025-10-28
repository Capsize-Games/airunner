"""Unit tests for Canvas Position Manager.

These tests ensure the positioning system works correctly and catches regressions.
"""

from PySide6.QtCore import QPointF

from airunner.components.art.utils.canvas_position_manager import (
    CanvasPositionManager,
    ViewState,
)


class TestViewState:
    """Test ViewState data class."""

    def test_default_grid_compensation(self):
        """Grid compensation should default to (0,0)."""
        state = ViewState(canvas_offset=QPointF(10, 20))
        assert state.grid_compensation == QPointF(0, 0)

    def test_total_offset_no_compensation(self):
        """Total offset with no compensation should equal canvas_offset."""
        state = ViewState(
            canvas_offset=QPointF(100, 200), grid_compensation=QPointF(0, 0)
        )
        assert state.total_offset == QPointF(100, 200)

    def test_total_offset_with_compensation(self):
        """Total offset should be canvas_offset - grid_compensation."""
        state = ViewState(
            canvas_offset=QPointF(100, 200), grid_compensation=QPointF(10, 20)
        )
        # total = 100 - 10, 200 - 20 = (90, 180)
        assert state.total_offset == QPointF(90, 180)


class TestAbsoluteToDisplay:
    """Test converting absolute positions to display positions."""

    def test_no_offset(self):
        """With no offset, positions should be identical."""
        manager = CanvasPositionManager()
        state = ViewState(canvas_offset=QPointF(0, 0))
        result = manager.absolute_to_display(QPointF(100, 200), state)
        assert result == QPointF(100, 200)

    def test_with_canvas_offset(self):
        """Canvas offset should shift display position."""
        manager = CanvasPositionManager()
        state = ViewState(canvas_offset=QPointF(50, 75))
        # display = 100 - 50, 200 - 75 = (50, 125)
        result = manager.absolute_to_display(QPointF(100, 200), state)
        assert result == QPointF(50, 125)

    def test_with_grid_compensation(self):
        """Grid compensation should counter canvas offset."""
        manager = CanvasPositionManager()
        state = ViewState(
            canvas_offset=QPointF(100, 200), grid_compensation=QPointF(10, 20)
        )
        # total_offset = 100 - 10, 200 - 20 = (90, 180)
        # display = 200 - 90, 300 - 180 = (110, 120)
        result = manager.absolute_to_display(QPointF(200, 300), state)
        assert result == QPointF(110, 120)

    def test_negative_positions(self):
        """Should handle negative positions correctly."""
        manager = CanvasPositionManager()
        state = ViewState(canvas_offset=QPointF(50, 50))
        result = manager.absolute_to_display(QPointF(-10, -20), state)
        assert result == QPointF(-60, -70)


class TestDisplayToAbsolute:
    """Test converting display positions to absolute positions."""

    def test_no_offset(self):
        """With no offset, positions should be identical."""
        manager = CanvasPositionManager()
        state = ViewState(canvas_offset=QPointF(0, 0))
        result = manager.display_to_absolute(QPointF(100, 200), state)
        assert result == QPointF(100, 200)

    def test_with_canvas_offset(self):
        """Canvas offset should shift absolute position."""
        manager = CanvasPositionManager()
        state = ViewState(canvas_offset=QPointF(50, 75))
        # absolute = 100 + 50, 200 + 75 = (150, 275)
        result = manager.display_to_absolute(QPointF(100, 200), state)
        assert result == QPointF(150, 275)

    def test_round_trip(self):
        """Converting to display and back should give original position."""
        manager = CanvasPositionManager()
        state = ViewState(
            canvas_offset=QPointF(123.5, 456.7),
            grid_compensation=QPointF(12.3, 45.6),
        )
        original = QPointF(500.5, 600.5)

        display = manager.absolute_to_display(original, state)
        back = manager.display_to_absolute(display, state)

        assert abs(back.x() - original.x()) < 0.01
        assert abs(back.y() - original.y()) < 0.01


class TestSnapToGrid:
    """Test grid snapping functionality."""

    def test_snap_disabled(self):
        """When disabled, position should not change."""
        manager = CanvasPositionManager()
        result = manager.snap_to_grid(
            QPointF(123.456, 789.012), cell_size=32, enabled=False
        )
        assert result == QPointF(123.456, 789.012)

    def test_snap_zero_cell_size(self):
        """With zero cell size, position should not change."""
        manager = CanvasPositionManager()
        result = manager.snap_to_grid(
            QPointF(123.456, 789.012), cell_size=0, enabled=True
        )
        assert result == QPointF(123.456, 789.012)

    def test_snap_to_origin_floor(self):
        """Snap to grid with origin at (0,0) using floor."""
        manager = CanvasPositionManager()
        # 123.456 / 32 = 3.858 -> floor = 3 -> 3 * 32 = 96
        # 789.012 / 32 = 24.657 -> floor = 24 -> 24 * 32 = 768
        result = manager.snap_to_grid(
            QPointF(123.456, 789.012), cell_size=32, use_floor=True
        )
        assert result == QPointF(96, 768)

    def test_snap_to_origin_round(self):
        """Snap to grid with origin at (0,0) using round."""
        manager = CanvasPositionManager()
        # 123.456 / 32 = 3.858 -> round = 4 -> 4 * 32 = 128
        # 789.012 / 32 = 24.657 -> round = 25 -> 25 * 32 = 800
        result = manager.snap_to_grid(
            QPointF(123.456, 789.012), cell_size=32, use_floor=False
        )
        assert result == QPointF(128, 800)

    def test_snap_with_grid_origin(self):
        """Snap should account for grid origin offset."""
        manager = CanvasPositionManager()
        grid_origin = QPointF(100, 200)
        # Relative: (150, 250) - (100, 200) = (50, 50)
        # Snapped: (50 / 32 = 1.5625 -> floor = 1 -> 1 * 32 = 32)
        # Absolute: (32, 32) + (100, 200) = (132, 232)
        result = manager.snap_to_grid(
            QPointF(150, 250),
            cell_size=32,
            grid_origin=grid_origin,
            use_floor=True,
        )
        assert result == QPointF(132, 232)

    def test_snap_negative_positions(self):
        """Should handle negative positions correctly."""
        manager = CanvasPositionManager()
        # -45 / 32 = -1.40625 -> floor = -2 -> -2 * 32 = -64
        result = manager.snap_to_grid(
            QPointF(-45, -70), cell_size=32, use_floor=True
        )
        assert result == QPointF(-64, -96)


class TestGetCenteredPosition:
    """Test calculating centered positions."""

    def test_square_item_in_square_viewport(self):
        """Center a square item in a square viewport."""
        manager = CanvasPositionManager()
        result = manager.get_centered_position(
            item_size=(100, 100), viewport_size=(500, 500)
        )
        # (500 - 100) / 2 = 200
        assert result == QPointF(200, 200)

    def test_small_item_in_large_viewport(self):
        """Center a small item in a large viewport."""
        manager = CanvasPositionManager()
        result = manager.get_centered_position(
            item_size=(64, 64), viewport_size=(1024, 768)
        )
        # x: (1024 - 64) / 2 = 480
        # y: (768 - 64) / 2 = 352
        assert result == QPointF(480, 352)

    def test_large_item_in_small_viewport(self):
        """Large item in small viewport should give negative position."""
        manager = CanvasPositionManager()
        result = manager.get_centered_position(
            item_size=(600, 400), viewport_size=(200, 200)
        )
        # x: (200 - 600) / 2 = -200
        # y: (200 - 400) / 2 = -100
        assert result == QPointF(-200, -100)


class TestCalculateDragPosition:
    """Test drag position calculations."""

    def test_drag_without_snap(self):
        """Drag without snapping should add delta to initial position."""
        manager = CanvasPositionManager()
        state = ViewState(canvas_offset=QPointF(0, 0))

        abs_pos, disp_pos = manager.calculate_drag_position(
            initial_absolute_pos=QPointF(100, 200),
            mouse_delta=QPointF(50, 75),
            view_state=state,
            snap_enabled=False,
        )

        assert abs_pos == QPointF(150, 275)
        assert disp_pos == QPointF(150, 275)

    def test_drag_with_snap(self):
        """Drag with snapping should snap the new absolute position."""
        manager = CanvasPositionManager()
        state = ViewState(canvas_offset=QPointF(0, 0))

        # 100 + 50 = 150, 200 + 75 = 275
        # Snap: 150 / 32 = 4.6875 -> floor = 4 -> 4 * 32 = 128
        #       275 / 32 = 8.59375 -> floor = 8 -> 8 * 32 = 256
        abs_pos, disp_pos = manager.calculate_drag_position(
            initial_absolute_pos=QPointF(100, 200),
            mouse_delta=QPointF(50, 75),
            view_state=state,
            cell_size=32,
            snap_enabled=True,
        )

        assert abs_pos == QPointF(128, 256)
        assert disp_pos == QPointF(128, 256)

    def test_drag_with_snap_and_grid_origin(self):
        """Drag with snap and grid origin should snap relative to origin."""
        manager = CanvasPositionManager()
        state = ViewState(canvas_offset=QPointF(0, 0))
        grid_origin = QPointF(64, 64)

        # New pos: 100 + 50 = 150, 200 + 75 = 275
        # Relative: (150 - 64, 275 - 64) = (86, 211)
        # Snap: 86 / 32 = 2.6875 -> floor = 2 -> 64
        #       211 / 32 = 6.59375 -> floor = 6 -> 192
        # Absolute: (64 + 64, 192 + 64) = (128, 256)
        abs_pos, disp_pos = manager.calculate_drag_position(
            initial_absolute_pos=QPointF(100, 200),
            mouse_delta=QPointF(50, 75),
            view_state=state,
            cell_size=32,
            grid_origin=grid_origin,
            snap_enabled=True,
        )

        assert abs_pos == QPointF(128, 256)

    def test_drag_with_view_offset(self):
        """Drag with view offset should calculate correct display position."""
        manager = CanvasPositionManager()
        state = ViewState(
            canvas_offset=QPointF(50, 100), grid_compensation=QPointF(5, 10)
        )

        # New absolute: 100 + 30 = 130, 200 + 40 = 240
        # total_offset = (50 - 5, 100 - 10) = (45, 90)
        # Display: (130 - 45, 240 - 90) = (85, 150)
        abs_pos, disp_pos = manager.calculate_drag_position(
            initial_absolute_pos=QPointF(100, 200),
            mouse_delta=QPointF(30, 40),
            view_state=state,
            snap_enabled=False,
        )

        assert abs_pos == QPointF(130, 240)
        assert disp_pos == QPointF(85, 150)
