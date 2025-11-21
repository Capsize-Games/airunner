"""Mixin for managing canvas items and their positioning."""

from typing import Optional

from PySide6.QtGui import QImage

from airunner.components.art.gui.widgets.canvas.draggables.layer_image_item import (
    LayerImageItem,
)


class CanvasItemManagementMixin:
    """Handles creation and management of canvas items.

    This mixin provides methods for creating, updating, and managing
    LayerImageItem instances on the canvas.
    """

    def _create_new_item(self, image: QImage, x: int, y: int) -> None:
        """Create a new LayerImageItem and add it to the scene.

        Args:
            image: The QImage to display.
            x: X position for the item.
            y: Y position for the item.
        """
        self.item = LayerImageItem(image)
        if self.item.scene() is None:
            self.addItem(self.item)
            self.item.setPos(x, y)
            self.original_item_positions[self.item] = self.item.pos()

    def _update_existing_item(self, image: QImage, x: int, y: int) -> None:
        """Update an existing item with new image and position.

        Args:
            image: The QImage to display.
            x: X position for the item.
            y: Y position for the item.
        """
        self.item.setPos(x, y)
        self.original_item_positions[self.item] = self.item.pos()
        if image is not None and not image.isNull():
            try:
                self.item.updateImage(image)
            except Exception:
                self.logger.warning(
                    "Failed to update existing item with new image."
                )

    def set_item(
        self,
        image: Optional[QImage] = None,
        z_index: int = 5,
        x: Optional[int] = None,
        y: Optional[int] = None,
    ) -> None:
        """Create or update the main canvas item with an image.

        Args:
            image: The QImage to display. If None, no item is created.
            z_index: The z-order for the item (default: 5).
            x: X position for the item. If None, uses grid settings.
            y: Y position for the item. If None, uses grid settings.
        """
        self.setSceneRect(self._extended_viewport_rect)

        if image is not None:
            x = self.active_grid_settings.pos_x if x is None else x
            y = self.active_grid_settings.pos_y if y is None else y

            # Check if we have layer items - if so, don't use the old drawing pad item system
            if len(self._layer_items) > 0:
                return

            if self.item is None:
                self._create_new_item(image, x, y)
            else:
                self._update_existing_item(image, x, y)

            self.item.setZValue(z_index)
            self.item.setVisible(True)

    def clear_selection(self) -> None:
        """Clear both selection start and stop positions."""
        self.selection_start_pos = None
        self.selection_stop_pos = None
