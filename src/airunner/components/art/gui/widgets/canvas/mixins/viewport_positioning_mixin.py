"""Viewport positioning mixin for CustomGraphicsView.

This mixin handles viewport-relative positioning calculations, layer position
management, and viewport compensation for window resizes.
"""

from typing import Dict, Tuple, Optional
from PySide6.QtCore import QPointF

from airunner.components.art.data.canvas_layer import CanvasLayer
from airunner.components.art.data.drawingpad_settings import DrawingPadSettings
from airunner.components.art.utils.canvas_position_manager import (
    CanvasPositionManager,
    ViewState,
)


class ViewportPositioningMixin:
    """Mixin for viewport positioning and layer position management.

    This mixin handles:
    - Viewport center calculations
    - Item recentering within viewport
    - Layer position loading from database
    - Layer position recalculation and saving
    - Canvas items alignment to viewport
    - Active grid area position updates
    - Image position updates based on canvas offset
    - Viewport compensation for window resizes

    Attributes:
        center_pos: Grid origin position (QPointF)
        _grid_compensation_offset: Viewport compensation offset
    """

    @property
    def viewport_center(self) -> QPointF:
        """Calculate the center point of the current viewport.

        Returns:
            Center point of viewport as QPointF.
        """
        viewport_size = self.viewport().size()
        return QPointF(viewport_size.width() / 2, viewport_size.height() / 2)

    def get_recentered_position(
        self, width: float, height: float
    ) -> Tuple[float, float]:
        """Calculate position to center an item of given size in the viewport.

        Args:
            width: Width of item to center.
            height: Height of item to center.

        Returns:
            Tuple of (x, y) coordinates for top-left corner to center the item.
        """
        viewport_center_x = self.viewport_center.x()
        viewport_center_y = self.viewport_center.y()

        item_center_x = width / 2.0
        item_center_y = height / 2.0

        target_x = viewport_center_x - item_center_x
        target_y = viewport_center_y - item_center_y

        return target_x, target_y

    def original_item_positions(self) -> Dict[str, QPointF]:
        """Get the absolute positions of all layer items from the database.

        This method reads saved positions - it does NOT recalculate or modify them.
        Use recenter_layer_positions() to explicitly reposition layers.

        Returns:
            Dictionary mapping scene items to their absolute positions.
        """
        layers = CanvasLayer.objects.order_by("order").all()
        original_item_positions = {}
        for index, layer in enumerate(layers):
            results = DrawingPadSettings.objects.filter_by(layer_id=layer.id)
            if len(results) == 0:
                continue

            drawingpad_settings = results[0]
            scene_item = self.scene._layer_items.get(layer.id)
            if scene_item is None:
                # Layer may not have been materialized yet; skip safely
                continue

            # Read the saved absolute position from the database
            # Do NOT recalculate - preserve what was saved
            if (
                drawingpad_settings.x_pos is not None
                and drawingpad_settings.y_pos is not None
            ):
                pos_x = drawingpad_settings.x_pos
                pos_y = drawingpad_settings.y_pos
            else:
                # If no saved position exists, use center of viewport as fallback
                item_rect = scene_item.boundingRect()
                image_width = item_rect.width()
                image_height = item_rect.height()
                pos_x, pos_y = self.get_recentered_position(
                    int(image_width), int(image_height)
                )
                # Save this calculated position for future use
                DrawingPadSettings.objects.update(
                    drawingpad_settings.id,
                    x_pos=pos_x,
                    y_pos=pos_y,
                )

            original_item_positions[scene_item] = QPointF(pos_x, pos_y)
        return original_item_positions

    def align_canvas_items_to_viewport(self) -> None:
        """Align canvas items (grid and layers) to viewport center.

        Calculates center position if needed, updates grid settings,
        and positions all items appropriately.
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

    def update_active_grid_area_position(self) -> None:
        """Update the active grid area position based on current offsets.

        Uses CanvasPositionManager to convert absolute position to display
        position accounting for canvas offset and grid compensation.
        """
        # Skip update during drag to prevent snap-back
        if self.scene and getattr(self.scene, "is_dragging", False):
            self.logger.info(
                "[ACTIVE GRID] Skipping position update - is_dragging is True"
            )
            return

        if self.active_grid_area:
            self.logger.info(
                f"[ACTIVE GRID] update_active_grid_area_position called - current scenePos: {self.active_grid_area.scenePos().x()}, {self.active_grid_area.scenePos().y()}"
            )
            self.logger.info(
                f"[ACTIVE GRID] Settings pos: {self.active_grid_settings.pos_x}, {self.active_grid_settings.pos_y}"
            )

            manager = CanvasPositionManager()
            view_state = ViewState(
                canvas_offset=QPointF(
                    self.canvas_offset_x, self.canvas_offset_y
                ),
                grid_compensation=self._grid_compensation_offset,
            )

            # Convert absolute position to display position
            abs_pos = QPointF(*self.active_grid_settings.pos)
            display_pos = manager.absolute_to_display(abs_pos, view_state)

            self.logger.info(
                f"[ACTIVE GRID] Setting position to display_pos: {display_pos.x()}, {display_pos.y()}"
            )
            self.active_grid_area.setPos(display_pos)

            actual_pos = self.active_grid_area.scenePos()
            self.logger.info(
                f"[ACTIVE GRID] After setPos, actual scenePos: {actual_pos.x()}, {actual_pos.y()}"
            )

    def updateImagePositions(
        self, original_item_positions: Optional[Dict[str, QPointF]] = None
    ) -> None:
        """Update positions of all images in the scene based on canvas offset.

        Args:
            original_item_positions: Optional dict mapping items to absolute positions.
                If None, positions are loaded from database.
        """
        if not self.scene:
            self.logger.error("No scene in updateImagePositions")
            return

        # Use the scene's update_image_position method which handles both
        # the old single-item system and the new layer system
        self.scene.update_image_position(
            self.canvas_offset, original_item_positions
        )

        # Force entire viewport update to handle negative coordinates
        self.viewport().update()
        
    def _apply_viewport_compensation(
        self, shift_x: float, shift_y: float
    ) -> None:
        """Apply viewport center compensation by adjusting grid compensation offset.

        This method shifts only the grid compensation offset so items appear to stay
        centered relative to the viewport, without changing the canvas_offset value
        or the stored absolute positions in the database.

        The CanvasPositionManager will automatically apply the grid_compensation
        when converting absolute positions to display positions.

        Args:
            shift_x: Horizontal shift in viewport center (pixels).
            shift_y: Vertical shift in viewport center (pixels).
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
