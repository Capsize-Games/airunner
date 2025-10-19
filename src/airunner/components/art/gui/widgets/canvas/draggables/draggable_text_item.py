from PySide6.QtCore import (
    QPointF,
    Qt,
)
from PySide6.QtWidgets import (
    QGraphicsTextItem,
    QMenu,
)
from airunner.enums import CanvasToolName
from airunner.components.art.utils.canvas_position_manager import (
    CanvasPositionManager,
    ViewState,
)


class DraggableTextItem(QGraphicsTextItem):
    """A text item that supports dragging in MOVE tool and reports position changes back to the view."""

    def __init__(self, view: "CustomGraphicsView"):
        super().__init__()
        self._view = view
        self.initial_mouse_scene_pos = None
        self.initial_item_abs_pos = None
        self.mouse_press_pos = None
        self._current_snapped_pos = (0, 0)

    @property
    def current_tool(self):
        try:
            return self._view.current_tool
        except Exception:
            return None

    def mousePressEvent(self, event):
        # Only initiate custom drag when in MOVE tool
        if self.current_tool not in [CanvasToolName.MOVE]:
            return QGraphicsTextItem.mousePressEvent(self, event)

        if event.button() == Qt.MouseButton.LeftButton:
            self.initial_mouse_scene_pos = event.scenePos()

            # Use the item's current scene position to compute initial absolute
            # coordinates for dragging. Previously this used persisted layer
            # settings which could be stale, causing the item to jump when the
            # user started dragging. Using scenePos() (plus canvas offset)
            # reflects the true displayed position and prevents the jump.
            try:
                item_scene_pos = self.scenePos()
                canvas_offset = self._view.canvas_offset
                abs_x = item_scene_pos.x() + canvas_offset.x()
                abs_y = item_scene_pos.y() + canvas_offset.y()
            except Exception:
                abs_x = int(self.x() + self._view.canvas_offset_x)
                abs_y = int(self.y() + self._view.canvas_offset_y)

            self.initial_item_abs_pos = QPointF(abs_x, abs_y)
            self.mouse_press_pos = event.pos()
            event.accept()
        else:
            # Show a simple context menu on right-click to delete the text
            if event.button() == Qt.MouseButton.RightButton:
                try:
                    menu = QMenu()
                    delete_action = menu.addAction(self.tr("Delete"))
                    chosen = menu.exec_(event.screenPos())
                    if chosen == delete_action:
                        view = getattr(self, "_view", None)
                        if view is not None:
                            view._remove_text_item(self)
                        return
                except Exception:
                    pass
                return
            return QGraphicsTextItem.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if self.current_tool not in [CanvasToolName.MOVE]:
            return QGraphicsTextItem.mouseMoveEvent(self, event)

        if self.initial_mouse_scene_pos is not None:
            delta = event.scenePos() - self.initial_mouse_scene_pos
            proposed_abs_pos = self.initial_item_abs_pos + delta

            # Get view state
            view_state = ViewState(
                canvas_offset=self._view.canvas_offset,
                grid_compensation=getattr(
                    self._view, "grid_compensation_offset", QPointF(0, 0)
                ),
            )

            manager = CanvasPositionManager()

            # Snap to grid if enabled
            if self._view.grid_settings.snap_to_grid:
                snapped_abs_pos = manager.snap_to_grid(
                    proposed_abs_pos, self._view.grid_settings.cell_size
                )
            else:
                snapped_abs_pos = proposed_abs_pos

            # Convert to display position
            display_pos = manager.absolute_to_display(
                snapped_abs_pos, view_state
            )
            self.setPos(display_pos)
            self._current_snapped_pos = (
                int(snapped_abs_pos.x()),
                int(snapped_abs_pos.y()),
            )
            event.accept()
        else:
            return QGraphicsTextItem.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        if self.current_tool not in [CanvasToolName.MOVE]:
            return QGraphicsTextItem.mouseReleaseEvent(self, event)

        if self.initial_mouse_scene_pos is not None:
            has_moved = False
            if self.mouse_press_pos:
                has_moved = (
                    self.mouse_press_pos.x() != event.pos().x()
                    or self.mouse_press_pos.y() != event.pos().y()
                )

            self.initial_mouse_scene_pos = None
            self.initial_item_abs_pos = None
            self.mouse_press_pos = None

            if has_moved:
                # Persist via view's save routine (which groups by layer)
                try:
                    self._view._save_text_items_to_db()
                except Exception:
                    # fallback to calling public method
                    try:
                        self._view._save_text_items_to_db()
                    except Exception:
                        pass
            event.accept()
        else:
            return QGraphicsTextItem.mouseReleaseEvent(self, event)
