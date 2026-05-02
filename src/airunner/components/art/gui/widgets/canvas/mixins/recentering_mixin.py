"""Mixin for recentering logic in CustomGraphicsView.

This mixin handles grid and layer recentering operations.
"""

from PySide6.QtCore import QPointF


class RecenteringMixin:
    """Provides recentering functionality for graphics view.

    This mixin manages:
    - Grid recentering
    - Layer position recentering
    - Canvas offset reset

    Dependencies:
        - self.scene: CustomScene instance
        - self.logger: Logging instance
        - self.canvas_offset: QPointF canvas offset property
        - self._grid_compensation_offset: QPointF grid compensation
        - self.center_pos: QPointF center position
        - self.application_settings: Application settings
        - self.get_recentered_position(): Calculate centered position
        - self.update_active_grid_settings(): Update grid settings
        - self.save_canvas_offset(): Save offset to settings
        - self.api: API instance
        - self.update_active_grid_area_position(): Update grid position
        - self.recenter_layer_positions(): Recenter all layers
        - self.update_drawing_pad_settings(): Update drawing pad settings
        - self.updateImagePositions(): Update image positions
    """

    def on_recenter_grid_signal(self):
        """Handle recenter grid signal.

        Reset the view and recenter only the grid origin.

        This keeps image layers and the active grid area's absolute
        positions intact while restoring the viewport and grid origin to
        a centered state.
        """
        # Reset offsets
        self.canvas_offset = QPointF(0, 0)
        self._grid_compensation_offset = QPointF(0, 0)

        if not self.scene:
            return

        # Calculate new center position for active grid area
        pos_x, pos_y = self.get_recentered_position(
            self.application_settings.working_width,
            self.application_settings.working_height,
        )
        self.center_pos = QPointF(pos_x, pos_y)

        # Save the reset offset
        self.save_canvas_offset()

        # Notify API of grid info update
        self.api.art.canvas.update_grid_info(
            {
                "offset_x": self.canvas_offset_x,
                "offset_y": self.canvas_offset_y,
            }
        )

        # Update active grid area display position
        self.update_active_grid_area_position()

        # Re-render items using their existing absolute positions.
        self.updateImagePositions()

        self.logger.info("[RECENTER] Recenter grid signal processing complete")

    def _preview_centered_layout(self) -> None:
        """Apply centered positions in memory before startup restoration ends.

        This avoids painting stale persisted positions for zero-offset canvases
        while the main window is still settling. Persistence is deferred until
        the final restoration step.
        """
        if not self.scene:
            return

        self.canvas_offset = QPointF(0, 0)
        self._grid_compensation_offset = QPointF(0, 0)

        pos_x, pos_y = self.get_recentered_position(
            self.application_settings.working_width,
            self.application_settings.working_height,
        )
        self.center_pos = QPointF(pos_x, pos_y)

        try:
            active_grid = self.active_grid_settings
            active_grid.pos_x = int(pos_x)
            active_grid.pos_y = int(pos_y)
        except Exception:
            pass

        new_positions = self._build_centered_preview_positions()
        if hasattr(self.scene, "original_item_positions"):
            self.scene.original_item_positions = {}

        self.update_active_grid_area_position()
        self.updateImagePositions(new_positions)

    def _build_centered_preview_positions(self) -> dict:
        """Return centered absolute positions for currently materialized items."""
        if not self.scene:
            return {}

        new_positions = {}
        centered_x, centered_y = self.get_recentered_position(
            self.application_settings.working_width,
            self.application_settings.working_height,
        )

        if self.scene.item:
            item_rect = self.scene.item.boundingRect()
            item_pos_x, item_pos_y = self.get_recentered_position(
                int(item_rect.width()),
                int(item_rect.height()),
            )
            new_positions[self.scene.item] = QPointF(item_pos_x, item_pos_y)

        for layer_item in getattr(self.scene, "_layer_items", {}).values():
            if layer_item is None:
                continue
            new_positions[layer_item] = QPointF(centered_x, centered_y)

        return new_positions
