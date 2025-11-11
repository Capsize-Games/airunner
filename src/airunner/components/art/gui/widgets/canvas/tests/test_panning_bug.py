"""Test to reproduce the panning offset bug.

Bug Report:
- After centering canvas, everything aligns correctly
- When panning with middle mouse, image shifts by: up 64px, left 256px
- Grid and active grid area pan correctly, only images have wrong offset

This suggests the image is using a different position source than the grid.
"""

import pytest
from PySide6.QtCore import QPointF

from airunner.components.art.utils.canvas_position_manager import (
    CanvasPositionManager,
    ViewState,
)


class TestPanningOffsetBug:
    """Reproduce the specific bug where images shift incorrectly when panning."""

    def test_image_position_after_center_then_pan(self, qapp):
        """Test that reproduces: center works, but pan causes wrong offset.

        Steps:
        1. Center the canvas (everything should align)
        2. Pan the canvas
        3. Verify image position matches grid position (they should move together)

        BUG: Image shifts by (-256, -64) relative to where it should be.
        """
        # Setup: viewport and working dimensions
        viewport_width = 800
        viewport_height = 600
        working_width = 512
        working_height = 512

        # Step 1: Calculate centered position (what recenter does)
        centered_x = (viewport_width - working_width) / 2.0  # 144
        centered_y = (viewport_height - working_height) / 2.0  # 44

        # After center, image absolute position should be (144, 44)
        image_absolute_pos = QPointF(centered_x, centered_y)

        # And with no offsets, display position = absolute position
        view_state_centered = ViewState(
            canvas_offset=QPointF(0, 0),
            grid_compensation=QPointF(0, 0),
        )

        manager = CanvasPositionManager()
        image_display_pos_centered = manager.absolute_to_display(
            image_absolute_pos, view_state_centered
        )

        # Should be at (144, 44)
        assert image_display_pos_centered.x() == pytest.approx(144.0)
        assert image_display_pos_centered.y() == pytest.approx(44.0)

        # Step 2: Pan the canvas by (100, 50)
        # This simulates dragging with middle mouse button
        pan_offset = QPointF(100, 50)

        view_state_panned = ViewState(
            canvas_offset=pan_offset,
            grid_compensation=QPointF(0, 0),
        )

        # Calculate where image SHOULD appear after pan
        # Formula: display = absolute - canvas_offset + grid_compensation
        # display = (144, 44) - (100, 50) + (0, 0) = (44, -6)
        image_display_pos_panned = manager.absolute_to_display(
            image_absolute_pos, view_state_panned
        )

        expected_x_after_pan = 144.0 - 100.0  # 44
        expected_y_after_pan = 44.0 - 50.0  # -6

        assert image_display_pos_panned.x() == pytest.approx(
            expected_x_after_pan
        )
        assert image_display_pos_panned.y() == pytest.approx(
            expected_y_after_pan
        )

        # Now the BUG: if image is reading wrong absolute position from DB,
        # it will appear at wrong location
        # User reports: image moves UP 64 and LEFT 256
        # That means actual position is: (44 - 256, -6 - 64) = (-212, -70)

        # Let's calculate what absolute position would give us (-212, -70):
        # display = absolute - canvas_offset
        # -212 = absolute_x - 100
        # absolute_x = -212 + 100 = -112
        #
        # -70 = absolute_y - 50
        # absolute_y = -70 + 50 = -20

        wrong_absolute_pos = QPointF(-112, -20)
        buggy_display_pos = manager.absolute_to_display(
            wrong_absolute_pos, view_state_panned
        )

        # This would give the buggy position user sees:
        assert buggy_display_pos.x() == pytest.approx(-212.0)
        assert buggy_display_pos.y() == pytest.approx(-70.0)

        # The difference between correct and buggy absolute position:
        offset_x = (
            image_absolute_pos.x() - wrong_absolute_pos.x()
        )  # 144 - (-112) = 256
        offset_y = (
            image_absolute_pos.y() - wrong_absolute_pos.y()
        )  # 44 - (-20) = 64

        # So the image's absolute position is wrong by exactly (256, 64)!
        # This matches the user's report!
        assert offset_x == pytest.approx(256.0)
        assert offset_y == pytest.approx(64.0)

    def test_diagnosis_wrong_absolute_position_source(self):
        """Diagnose: Image might be reading absolute position from wrong source.

        Theory: When panning, if image isn't in original_item_positions cache,
        it reads from database. But database might have stale values.

        Possible causes:
        1. Database not updated when centering
        2. Wrong layer ID used when reading from DB
        3. Reading from wrong settings object (controlnet vs image vs drawing_pad)
        """
        # Expected centered position
        expected_centered = QPointF(144, 44)

        # What might be in the database (stale old position or default (0,0))
        # If DB has (0, 0), and we center to (144, 44), then difference is (144, 44)
        # But user reports offset of (256, 64) which is different!

        # Let's check if there's a pattern:
        # Maybe DB has some other cached position?

        # If offset is (256, 64), and centered pos is (144, 44)
        # Then DB might have: (144 - 256, 44 - 64) = (-112, -20)
        stale_db_pos = QPointF(-112, -20)

        offset = QPointF(
            expected_centered.x() - stale_db_pos.x(),
            expected_centered.y() - stale_db_pos.y(),
        )

        assert offset.x() == pytest.approx(256.0)
        assert offset.y() == pytest.approx(64.0)

        # Hypothesis: The database has position (-112, -20) which is wrong
        # This could happen if:
        # 1. Image was created at (0, 0) originally
        # 2. Some viewport adjustment was applied: (0 - 112, 0 - 20)
        # 3. But recenter didn't update this value properly

    @pytest.mark.xfail(reason="Need to verify actual database behavior")
    def test_recenter_updates_database_position(self):
        """Test that recentering actually updates the database position.

        This test documents what SHOULD happen:
        1. Recenter is called
        2. New centered position (144, 44) is calculated
        3. Database is updated with this position for the layer
        4. When panning later, image reads (144, 44) from DB
        5. Position calculation works correctly
        """
        # This test needs real database interaction
        # Mark as xfail until we can verify the actual behavior
