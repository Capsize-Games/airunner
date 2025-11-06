"""Mixin for pan and offset management in CustomGraphicsView.

This mixin handles canvas panning, viewport compensation, and item alignment.
"""

from PySide6.QtCore import QPointF


class PanOffsetMixin:
    """Provides pan and offset management for graphics view.

    This mixin manages:
    - Pan update handling
    - Viewport compensation during resize
    - Canvas item alignment to viewport

    Dependencies:
        - self.scene: CustomScene instance
        - self.logger: Logging instance
        - self.canvas_offset: QPointF canvas offset property
        - self._grid_compensation_offset: QPointF grid compensation
        - self.center_pos: QPointF center position
        - self._is_restoring_state: Bool restoration flag
        - self._initialized: Bool initialization flag
        - self._pending_pan_event: Bool pending pan flag
        - self._pan_update_timer: QTimer for pan updates
        - self.application_settings: Application settings
        - self.settings: QSettings instance
        - self.api: API instance
        - self.update_active_grid_area_position(): Update grid position
        - self.updateImagePositions(): Update image positions
        - self.draw_grid(): Draw grid method
        - self.get_recentered_position(): Calculate centered position
        - self.update_active_grid_settings(): Update grid settings
        - self.original_item_positions(): Get original positions
        - self.save_canvas_offset(): Save offset to settings
    """

    def _do_pan_update(self):
        """Execute pan update by refreshing grid, images, and grid lines.

        This is called during panning to update all visual elements.
        If another pan event is pending, schedules another update.
        """
        self.update_active_grid_area_position()
        self.updateImagePositions()
        self.draw_grid()
        if self._pending_pan_event:
            self._pending_pan_event = False
            self._pan_update_timer.start(1)

    def _finish_state_restoration(self):
        """Complete state restoration and re-enable resize compensation.

        Called after a delay to finalize state restoration, reload canvas offset,
        and update all positions one final time.
        """
        self._is_restoring_state = False

        # Reload and reapply the canvas offset one final time to ensure it's correct
        x = self.settings.value("canvas_offset_x", 0.0)
        y = self.settings.value("canvas_offset_y", 0.0)
        # Handle None values from mocked settings
        x = float(x) if x is not None else 0.0
        y = float(y) if y is not None else 0.0
        final_offset = QPointF(x, y)
        self.canvas_offset = final_offset

        # Update positions one final time
        self.update_active_grid_area_position()
        self.updateImagePositions()

        self.logger.debug(
            f"Canvas state restoration complete - final offset: ({final_offset.x()}, {final_offset.y()})"
        )
        self.scene.show_event()

    def _apply_viewport_compensation(self, shift_x: float, shift_y: float):
        """Apply viewport center compensation by adjusting grid compensation offset.

        This shifts only the grid compensation offset so items appear to stay
        centered relative to the viewport, without changing the canvas_offset value
        or the stored absolute positions in the database.

        The CanvasPositionManager automatically applies the grid_compensation
        when converting absolute positions to display positions.

        Args:
            shift_x: Horizontal shift amount in pixels.
            shift_y: Vertical shift amount in pixels.
        """
        if not self.scene:
            return

        # Skip if the shift is negligible
        if abs(shift_x) < 0.5 and abs(shift_y) < 0.5:
            return

        self.logger.info(
            f"[VIEWPORT COMPENSATION] Applying shift: ({shift_x}, {shift_y}), "
            f"old_compensation=({self._grid_compensation_offset.x()}, {self._grid_compensation_offset.y()}), "
            f"_is_restoring_state={self._is_restoring_state}, _initialized={self._initialized}"
        )

        # Adjust the grid compensation offset
        # This shifts the grid origin to maintain alignment with the viewport center
        self._grid_compensation_offset = QPointF(
            self._grid_compensation_offset.x() + shift_x,
            self._grid_compensation_offset.y() + shift_y,
        )

        self.logger.info(
            f"[VIEWPORT COMPENSATION] New compensation: ({self._grid_compensation_offset.x()}, {self._grid_compensation_offset.y()})"
        )

        # DO NOT modify the scene's original_item_positions here!
        # The CanvasPositionManager.absolute_to_display() already applies
        # grid_compensation in its calculation:
        # display_pos = absolute_pos - canvas_offset + grid_compensation
        #
        # If we shift the absolute positions here, we would be double-applying
        # the compensation, causing items to drift during window resize.

        # Update the visual positions using the new grid_compensation
        # The position manager will automatically apply it
        self.update_active_grid_area_position()
        self.updateImagePositions()
        self.draw_grid()

    def align_canvas_items_to_viewport(self):
        """Align canvas items to viewport center.

        Calculates or uses loaded center position and updates grid and image positions.
        Only calculates new center if not already loaded from settings.
        """
        # Don't recalculate center_pos if it was loaded from settings
        # (this preserves the grid origin across app restarts)
        # Only calculate if center_pos is still at the default (0,0)
        if self.center_pos == QPointF(0, 0):
            pos_x, pos_y = self.get_recentered_position(
                self.application_settings.working_width,
                self.application_settings.working_height,
            )
            self.center_pos = QPointF(pos_x, pos_y)
            self.logger.info(
                f"[ALIGN] Center pos calculated: x={pos_x}, y={pos_y}"
            )
        else:
            # Use existing center_pos from loaded settings
            pos_x = int(self.center_pos.x())
            pos_y = int(self.center_pos.y())
            self.logger.info(
                f"[ALIGN] Using loaded center pos: x={pos_x}, y={pos_y}"
            )

        self.update_active_grid_settings(
            pos_x=pos_x,
            pos_y=pos_y,
        )
        # Update display positions
        self.update_active_grid_area_position()

        self.updateImagePositions(self.original_item_positions())
