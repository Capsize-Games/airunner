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

        Resets canvas offset and grid compensation, then recenters
        the active grid area and all layer images to viewport center.
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

        # Update grid settings with new position
        self.update_active_grid_settings(
            pos_x=pos_x,
            pos_y=pos_y,
        )

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

        # Recalculate and save new centered positions
        new_positions = {}

        # Handle old single-item system (DrawingPad item)
        if self.scene.item:
            self.logger.info(
                "[RECENTER] Processing old single-item system (DrawingPad)"
            )
            item_rect = self.scene.item.boundingRect()
            image_width = item_rect.width()
            image_height = item_rect.height()
            item_pos_x, item_pos_y = self.get_recentered_position(
                int(image_width), int(image_height)
            )

            # Save to database
            self.update_drawing_pad_settings(
                x_pos=item_pos_x, y_pos=item_pos_y
            )

            # Add to positions dict
            new_positions[self.scene.item] = QPointF(item_pos_x, item_pos_y)
            self.logger.info(
                f"[RECENTER] DrawingPad item: saved to DB and dict - position x={item_pos_x}, y={item_pos_y}"
            )

        # Handle new layer system
        layer_positions = self.recenter_layer_positions()
        new_positions.update(layer_positions)

        self.logger.info(
            f"[RECENTER] Total items to recenter: {len(new_positions)}"
        )

        # Clear caches AFTER saving to DB but BEFORE updating scene
        # This ensures scene.update_image_position() uses fresh DB values
        if hasattr(self.scene, "original_item_positions"):
            self.scene.original_item_positions = {}

        # Update all image positions with the new centered positions
        self.updateImagePositions(new_positions)
        
        # Store the new positions for future updates
        if hasattr(self.scene, "original_item_positions"):
            self.scene.original_item_positions.update(new_positions)

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
