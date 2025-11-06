"""Mixin for context menu handling in CustomGraphicsView.

This mixin handles right-click context menus for deleting items.
"""

from PySide6.QtWidgets import QMenu, QGraphicsPixmapItem

from airunner.components.art.gui.widgets.canvas.grid_graphics_item import (
    GridGraphicsItem,
)
from airunner.components.art.gui.widgets.canvas.draggables.active_grid_area import (
    ActiveGridArea,
)


class ContextMenuMixin:
    """Provides context menu functionality for graphics view.

    This mixin manages:
    - Right-click context menu display
    - Item deletion via context menu
    - Text item removal
    - Layer image item removal

    Dependencies:
        - self.mapToScene(): Qt method to map pos to scene
        - self.scene: CustomScene instance
        - self.tr(): Qt translation method
        - self._text_items: List of text items
        - self._remove_text_item(): Text removal method
        - self._remove_layer_image_item(): Layer image removal method
    """

    def contextMenuEvent(self, event):
        """Show delete context menu for items under cursor.

        Displays a context menu with delete action for deletable items
        (excluding grid and active grid area). Handles deletion of text
        items and pixmap items.

        Args:
            event: Qt context menu event.
        """
        try:
            scene_pos = self.mapToScene(event.pos())
        except Exception:
            return

        try:
            items = self.scene.items(scene_pos)
        except Exception:
            items = []

        if not items:
            return

        try:
            # Create context menu with delete action
            menu = QMenu()
            delete_action = menu.addAction(self.tr("Delete"))
            chosen = menu.exec_(event.globalPos())

            if chosen == delete_action:
                # Find first deletable item (skip grid and active grid area)
                deletable = None
                for candidate in items:
                    if not isinstance(
                        candidate, (GridGraphicsItem, ActiveGridArea)
                    ):
                        deletable = candidate
                        break

                if deletable is None:
                    return

                target = deletable

                # Handle text item deletion
                if target in getattr(self, "_text_items", []):
                    self._remove_text_item(target)
                # Handle pixmap item deletion (images)
                elif isinstance(target, QGraphicsPixmapItem):
                    self._remove_layer_image_item(target)
                # Handle other items
                else:
                    getattr(target, "layer_id", None)
                    self._remove_layer_image_item(target)
                    try:
                        if target.scene():
                            target.scene().removeItem(target)
                    except Exception:
                        pass
        except Exception:
            pass
