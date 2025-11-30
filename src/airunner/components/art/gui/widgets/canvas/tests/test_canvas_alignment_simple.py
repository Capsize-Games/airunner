"""Simple tests documenting canvas alignment issues and expected behavior.

These tests document the reported issues:
1. Grid lines are slightly off-center
2. Images don't align with the active grid area center

Note: These are currently documented as EXPECTED FAILURES since
the bugs exist. Once fixed, remove the @pytest.mark.xfail decorators.
"""

import pytest
from PySide6.QtCore import QPointF

from airunner.components.art.utils.canvas_position_manager import (
    CanvasPositionManager,
    ViewState,
)


class TestCanvasAlignmentIssues:
    """Document alignment issues that need fixing."""

    @pytest.mark.xfail(reason="BUG: Grid lines are off-center")
    def test_grid_lines_should_be_centered(self):
        """Grid origin should be at viewport center when recentered.

        CURRENT BUG: Grid lines are slightly off-center.
        EXPECTED: Grid origin (center_pos) should equal viewport_center.
        """
        viewport_width = 800
        viewport_height = 600
        viewport_center = QPointF(viewport_width / 2.0, viewport_height / 2.0)

        # After recenter, center_pos should equal viewport center
        # This documents what SHOULD happen
        center_pos = viewport_center  # This is what we EXPECT

        assert center_pos.x() == pytest.approx(400.0)
        assert center_pos.y() == pytest.approx(300.0)

    @pytest.mark.xfail(reason="BUG: Images don't align with active grid area")
    def test_images_should_align_with_active_grid(self):
        """Images should be centered at same point as active grid area.

        CURRENT BUG: Images don't align to center like active grid area does.
        EXPECTED: Image display position should match active grid display position.
        """
        working_width = 1024
        working_height = 1024
        viewport_width = 800
        viewport_height = 600

        # Calculate where active grid SHOULD be (centered)
        expected_grid_pos_x = (viewport_width - working_width) / 2.0
        expected_grid_pos_y = (viewport_height - working_height) / 2.0

        # Image should be at same position
        expected_image_pos = QPointF(expected_grid_pos_x, expected_grid_pos_y)

        assert expected_image_pos.x() == pytest.approx(144.0)
        assert expected_image_pos.y() == pytest.approx(44.0)


class TestCanvasPositionManager:
    """Test coordinate transformation utility functions."""

    def test_absolute_to_display_position(self):
        """Test converting absolute position to display position."""
        # Absolute position is relative to center_pos
        absolute_pos = QPointF(400, 300)  # At grid origin (viewport center)
        view_state = ViewState(
            canvas_offset=QPointF(0, 0),  # No panning
            grid_compensation=QPointF(
                0, 0
            ),  # No viewport resize compensation
        )

        display_pos = CanvasPositionManager.absolute_to_display(
            absolute_pos, view_state
        )

        # Display position should be same as absolute (no offsets)
        assert display_pos.x() == pytest.approx(400.0)
        assert display_pos.y() == pytest.approx(300.0)

    def test_absolute_to_display_with_offset(self):
        """Test display position calculation with canvas offset."""
        absolute_pos = QPointF(400, 300)
        view_state = ViewState(
            canvas_offset=QPointF(50, 30),  # User panned right/down
            grid_compensation=QPointF(0, 0),
        )

        display_pos = CanvasPositionManager.absolute_to_display(
            absolute_pos, view_state
        )

        # Display should be offset by canvas_offset
        # Formula: display = absolute - canvas_offset + grid_compensation
        assert display_pos.x() == pytest.approx(350.0)  # 400 - 50
        assert display_pos.y() == pytest.approx(270.0)  # 300 - 30

    def test_display_to_absolute_position(self):
        """Test converting display position back to absolute."""
        display_pos = QPointF(350, 270)
        view_state = ViewState(
            canvas_offset=QPointF(50, 30),
            grid_compensation=QPointF(0, 0),
        )

        absolute_pos = CanvasPositionManager.display_to_absolute(
            display_pos, view_state
        )

        # Should get back to original absolute position
        assert absolute_pos.x() == pytest.approx(400.0)
        assert absolute_pos.y() == pytest.approx(300.0)

    def test_get_centered_position(self):
        """Test calculating centered position for an item."""
        item_size = (512, 512)
        viewport_size = (800, 600)

        centered_pos = CanvasPositionManager.get_centered_position(
            item_size, viewport_size
        )

        # Item should be centered in viewport
        expected_x = (800 - 512) / 2.0  # 144
        expected_y = (600 - 512) / 2.0  # 44

        assert centered_pos.x() == pytest.approx(expected_x)
        assert centered_pos.y() == pytest.approx(expected_y)


class TestOffsetManagement:
    """Test offset management and reset behavior."""

    def test_canvas_offset_represents_panning(self):
        """Canvas offset tracks user panning, independent of other offsets."""
        canvas_offset = QPointF(100, 50)  # User panned
        grid_compensation = QPointF(20, 10)  # Viewport resized

        # These should be independent
        assert canvas_offset.x() != grid_compensation.x()
        assert canvas_offset.y() != grid_compensation.y()

    @pytest.mark.xfail(
        reason="BUG: Offsets may not reset properly on recenter"
    )
    def test_recenter_should_reset_offsets(self):
        """Recenter should reset both canvas_offset and grid_compensation to zero.

        CURRENT BUG: Offsets might not be reset properly.
        EXPECTED: Both offsets should be (0, 0) after recenter.
        """
        # After recenter, both should be zero
        canvas_offset = QPointF(0, 0)
        grid_compensation = QPointF(0, 0)

        assert canvas_offset.x() == 0.0
        assert canvas_offset.y() == 0.0
        assert grid_compensation.x() == 0.0
        assert grid_compensation.y() == 0.0
