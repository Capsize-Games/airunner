"""Canvas position update mixin for managing item positions."""

from typing import Optional, Dict
from PySide6.QtCore import QPointF
from airunner.components.art.data.drawingpad_settings import DrawingPadSettings
from airunner.components.art.utils.canvas_position_manager import CanvasPositionManager, ViewState
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.components.application.gui.windows.main.settings_mixin import (
    SettingsMixin,
)


class CanvasPositionUpdateMixin(MediatorMixin, SettingsMixin):
    """Handles position updates for canvas items.

    This mixin provides functionality for:
    - Updating item positions based on canvas offset
    - Managing original position tracking
    - Coordinating display positions with absolute coordinates
    - Handling layer-specific position management
    """

    def update_image_position(
        self,
        canvas_offset: QPointF,
        original_item_positions: Optional[Dict[str, QPointF]] = None,
    ) -> None:
        """Update positions of all items on the canvas based on canvas offset.

        Args:
            canvas_offset: The offset of the canvas viewport.
            original_item_positions: Optional dict mapping items to their
                original positions. If None, uses self.original_item_positions.
        """
        original_item_positions = (
            self.original_item_positions
            if original_item_positions is None
            else original_item_positions
        )

        # Get view for grid compensation offset
        view = self.views()[0] if self.views() else None
        grid_compensation = (
            getattr(view, "_grid_compensation_offset", QPointF(0, 0))
            if view
            else QPointF(0, 0)
        )

        # Create position manager and view state
        manager = CanvasPositionManager()
        view_state = ViewState(
            canvas_offset=canvas_offset,
            grid_compensation=grid_compensation,
        )

        # Update the old drawing pad item if it exists
        if self.item:
            self._update_main_item_position(
                original_item_positions, manager, view_state
            )

        # Update layer items
        self._update_layer_items_positions(
            original_item_positions, manager, view_state
        )

    def _update_main_item_position(
        self,
        original_item_positions: Dict,
        manager: CanvasPositionManager,
        view_state: ViewState,
    ) -> None:
        """Update the main drawing pad item position.

        Args:
            original_item_positions: Dict mapping items to original positions.
            manager: Position manager for coordinate conversions.
            view_state: Current view state with offsets.
        """
        if self.item not in original_item_positions:
            abs_x = self.drawing_pad_settings.x_pos
            abs_y = self.drawing_pad_settings.y_pos

            if abs_x is None or abs_y is None:
                abs_x = self.item.pos().x()
                abs_y = self.item.pos().y()

            original_item_positions[self.item] = QPointF(abs_x, abs_y)

        original_pos = original_item_positions[self.item]

        # Use CanvasPositionManager for coordinate conversion
        display_pos = manager.absolute_to_display(original_pos, view_state)
        new_x = display_pos.x()
        new_y = display_pos.y()

        try:
            current_pos = self.item.pos()
            if (
                abs(current_pos.x() - new_x) > 1
                or abs(current_pos.y() - new_y) > 1
            ):
                self.item.prepareGeometryChange()
                self.item.setPos(new_x, new_y)
                self.item.setVisible(True)
                rect = self.item.boundingRect().adjusted(-10, -10, 10, 10)
                scene_rect = self.item.mapRectToScene(rect)
                self.update(scene_rect)
        except (RuntimeError, AttributeError):
            # Item was deleted or is no longer valid
            pass

    def _update_layer_items_positions(
        self,
        original_item_positions: Dict,
        manager: CanvasPositionManager,
        view_state: ViewState,
    ) -> None:
        """Update positions for all layer items.

        Args:
            original_item_positions: Dict mapping items to original positions.
            manager: Position manager for coordinate conversions.
            view_state: Current view state with offsets.
        """
        # Create a copy of items to iterate over, as we might modify the dict
        layer_items_copy = list(self._layer_items.items())

        for layer_id, layer_item in layer_items_copy:
            try:
                self._ensure_layer_has_original_position(
                    layer_id, layer_item, original_item_positions
                )

                original_pos = original_item_positions[layer_item]
                self.logger.info(
                    f"[UPDATE_POS] Layer {layer_id}: using position "
                    f"x={original_pos.x()}, y={original_pos.y()}"
                )

                # Use CanvasPositionManager for coordinate conversion
                display_pos = manager.absolute_to_display(
                    original_pos, view_state
                )
                new_x = display_pos.x()
                new_y = display_pos.y()

                self._apply_layer_item_position(layer_item, new_x, new_y)

            except (RuntimeError, AttributeError):
                # Layer item was deleted or is no longer valid
                pass

    def _ensure_layer_has_original_position(
        self, layer_id: int, layer_item, original_item_positions: Dict
    ) -> None:
        """Ensure a layer has an entry in original_item_positions.

        Args:
            layer_id: ID of the layer.
            layer_item: The layer's QGraphicsItem.
            original_item_positions: Dict to update with position.
        """
        if layer_item not in original_item_positions:
            self.logger.info(
                f"[UPDATE_POS] Layer {layer_id} item (id={id(layer_item)}) "
                f"NOT in original_item_positions, reading from settings"
            )
            try:
                drawing_pad_settings = self._get_layer_specific_settings(
                    DrawingPadSettings, layer_id=layer_id
                )
                if drawing_pad_settings:
                    abs_x = drawing_pad_settings.x_pos or 0
                    abs_y = drawing_pad_settings.y_pos or 0
                else:
                    abs_x = layer_item.pos().x()
                    abs_y = layer_item.pos().y()

                original_item_positions[layer_item] = QPointF(abs_x, abs_y)
                self.logger.info(
                    f"[UPDATE_POS] Layer {layer_id}: read from settings "
                    f"x={abs_x}, y={abs_y}"
                )
            except Exception:
                current_pos = layer_item.pos()
                original_item_positions[layer_item] = current_pos
        else:
            self.logger.info(
                f"[UPDATE_POS] Layer {layer_id} item (id={id(layer_item)}) "
                f"FOUND in original_item_positions"
            )

    def _apply_layer_item_position(
        self, layer_item, new_x: float, new_y: float
    ) -> None:
        """Apply new position to a layer item.

        Args:
            layer_item: The layer's QGraphicsItem.
            new_x: New X coordinate.
            new_y: New Y coordinate.
        """
        try:
            current_pos = layer_item.pos()
            if (
                abs(current_pos.x() - new_x) > 1
                or abs(current_pos.y() - new_y) > 1
            ):
                layer_item.prepareGeometryChange()
                layer_item.setPos(new_x, new_y)
                layer_item.setVisible(True)
                rect = layer_item.boundingRect().adjusted(-10, -10, 10, 10)
                scene_rect = layer_item.mapRectToScene(rect)
                self.update(scene_rect)
        except (RuntimeError, AttributeError):
            # Layer item was deleted or is no longer valid
            pass
