from __future__ import annotations

from typing import Optional, Set, TYPE_CHECKING

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsRectItem,
    QGraphicsTextItem,
    QMenu,
)

from airunner.enums import CanvasToolName
from airunner.utils.application.snap_to_grid import snap_to_grid

if TYPE_CHECKING:
    from airunner.components.art.gui.widgets.canvas.custom_view import (
        CustomGraphicsView,
    )
else:  # pragma: no cover - avoid hard dependency during import cycles
    CustomGraphicsView = object


class ResizableTextItem(QGraphicsRectItem):
    """Rectangular text area that keeps text clipped and supports resizing."""

    MIN_WIDTH = 40.0
    MIN_HEIGHT = 40.0
    BORDER_MARGIN = 8.0

    _ANCHOR_TO_EDGES = {
        "left": {"left"},
        "right": {"right"},
        "top": {"top"},
        "bottom": {"bottom"},
        "top-left": {"top", "left"},
        "top-right": {"top", "right"},
        "bottom-left": {"bottom", "left"},
        "bottom-right": {"bottom", "right"},
    }

    def __init__(self, view: CustomGraphicsView, rect: QRectF):
        width = max(rect.width(), self.MIN_WIDTH)
        height = max(rect.height(), self.MIN_HEIGHT)
        super().__init__(QRectF(0.0, 0.0, width, height))

        self._view = view
        self.setPos(rect.topLeft())
        self.setZValue(2000)
        self.setPen(QPen(QColor("white")))
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(
            QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges, True
        )
        self.setFlag(
            QGraphicsRectItem.GraphicsItemFlag.ItemClipsChildrenToShape, True
        )
        self.setAcceptHoverEvents(True)

        self.text_item = QGraphicsTextItem(self)
        self.text_item.setDefaultTextColor(QColor("white"))
        try:
            self.text_item.setFont(self._view._get_default_text_font())
        except Exception:
            pass
        self.text_item.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.text_item.setPos(QPointF(0.0, 0.0))
        self.text_item.setTextWidth(width)
        self.text_item.setZValue(self.zValue() + 1)

        self._resizing = False
        self._resize_anchor: Optional[str] = None
        self._initial_geometry: tuple[float, float, float, float] = (
            rect.left(),
            rect.top(),
            rect.left() + width,
            rect.top() + height,
        )
        self._start_scene_pos = QPointF(rect.topLeft())
        self._initial_aspect = width / height if height > 0 else None

    @property
    def current_tool(self) -> Optional[CanvasToolName]:
        try:
            return self._view.current_tool
        except Exception:
            return None

    def setText(self, text: str) -> None:
        self.text_item.setPlainText(text)

    def set_interaction_enabled(self, enable: bool) -> None:
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable, enable)
        self.setFlag(
            QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, enable
        )
        self.text_item.setTextInteractionFlags(
            Qt.TextEditorInteraction if enable else Qt.NoTextInteraction
        )

    def hoverMoveEvent(self, event):
        anchor = self._detect_anchor(self.mapFromScene(event.scenePos()))
        cursor = self._cursor_for_anchor(anchor)
        if cursor is not None:
            self.setCursor(cursor)
        else:
            self.unsetCursor()
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        self.unsetCursor()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self._open_delete_menu(event)
            return

        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        anchor = self._detect_anchor(self.mapFromScene(event.scenePos()))
        if anchor is not None:
            self._begin_resize(anchor, event.scenePos())
            event.accept()
            return

        if self.current_tool != CanvasToolName.MOVE:
            self.text_item.setFocus()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resizing and self._resize_anchor:
            self._apply_resize(event.scenePos(), event.modifiers())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._resizing:
            self._finish_resize(event.scenePos())
            event.accept()
            return
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self._persist_geometry()

    def itemChange(self, change, value):
        if change == QGraphicsRectItem.GraphicsItemChange.ItemPositionChange:
            value = self._snap_position_if_needed(value)
        elif (
            change
            == QGraphicsRectItem.GraphicsItemChange.ItemPositionHasChanged
        ):
            self._persist_geometry()
        return super().itemChange(change, value)

    def paint(self, painter: QPainter, option, widget=None):
        super().paint(painter, option, widget)
        if not self.isSelected():
            return
        size = 6.0
        rect = self.rect()
        painter.save()
        painter.setPen(QPen(QColor("white")))
        painter.setBrush(QColor("white"))
        handle_rects = [
            QRectF(rect.left() - size / 2, rect.top() - size / 2, size, size),
            QRectF(rect.right() - size / 2, rect.top() - size / 2, size, size),
            QRectF(
                rect.left() - size / 2, rect.bottom() - size / 2, size, size
            ),
            QRectF(
                rect.right() - size / 2, rect.bottom() - size / 2, size, size
            ),
        ]
        for handle_rect in handle_rects:
            painter.drawRect(handle_rect)
        painter.restore()

    def to_persist_dict(self) -> dict:
        """Return a JSON-serializable representation of this item."""

        abs_x = int(self.scenePos().x() + self._view.canvas_offset_x)
        abs_y = int(self.scenePos().y() + self._view.canvas_offset_y)
        return {
            "type": "area",
            "text": self.text_item.toPlainText(),
            "x": abs_x,
            "y": abs_y,
            "color": self.text_item.defaultTextColor().name(),
            "font": self.text_item.font().toString(),
            "w": int(self.rect().width()),
            "h": int(self.rect().height()),
        }

    def _persist_geometry(self) -> None:
        if self._view is not None:
            try:
                self._view._save_text_items_to_db()
            except Exception:
                pass

    def _begin_resize(self, anchor: str, scene_pos: QPointF) -> None:
        self._resizing = True
        self._resize_anchor = anchor
        self._start_scene_pos = QPointF(scene_pos)
        self._capture_initial_geometry()
        self.text_item.setTextInteractionFlags(Qt.NoTextInteraction)

    def _apply_resize(
        self, scene_pos: QPointF, modifiers: Qt.KeyboardModifiers
    ) -> None:
        if not self._resizing or self._resize_anchor is None:
            return

        edges = self._ANCHOR_TO_EDGES[self._resize_anchor]
        delta = scene_pos - self._start_scene_pos
        left, top, right, bottom = self._initial_geometry

        if "left" in edges:
            left += delta.x()
        if "right" in edges:
            right += delta.x()
        if "top" in edges:
            top += delta.y()
        if "bottom" in edges:
            bottom += delta.y()

        left, right = self._enforce_min_width(edges, left, right)
        top, bottom = self._enforce_min_height(edges, top, bottom)

        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            left, right, top, bottom = self._apply_aspect_constraint(
                edges, left, right, top, bottom
            )

        left, right, top, bottom = self._apply_grid_snapping(
            edges, left, right, top, bottom
        )

        width = max(self.MIN_WIDTH, right - left)
        height = max(self.MIN_HEIGHT, bottom - top)

        self.prepareGeometryChange()
        self.setRect(QRectF(0.0, 0.0, width, height))
        self.setPos(QPointF(left, top))
        self.text_item.setTextWidth(width)

    def _finish_resize(self, scene_pos: QPointF) -> None:
        self._apply_resize(scene_pos, Qt.KeyboardModifier.NoModifier)
        self._resizing = False
        self._resize_anchor = None
        self.text_item.setTextInteractionFlags(Qt.TextEditorInteraction)
        self._persist_geometry()

    def _capture_initial_geometry(self) -> None:
        rect = self.rect()
        pos = self.scenePos()
        self._initial_geometry = (
            pos.x(),
            pos.y(),
            pos.x() + rect.width(),
            pos.y() + rect.height(),
        )
        height = rect.height()
        self._initial_aspect = rect.width() / height if height > 0 else None

    def _apply_aspect_constraint(
        self,
        edges: Set[str],
        left: float,
        right: float,
        top: float,
        bottom: float,
    ) -> tuple[float, float, float, float]:
        if not self._initial_aspect:
            return left, right, top, bottom

        width = max(self.MIN_WIDTH, right - left)
        height = max(self.MIN_HEIGHT, bottom - top)
        target_height = width / self._initial_aspect
        target_width = height * self._initial_aspect
        anchor = self._resize_anchor or ""

        if anchor in {"left", "right"}:
            height = target_height
            if "top" in edges and "bottom" not in edges:
                top = bottom - height
            else:
                bottom = top + height
        elif anchor in {"top", "bottom"}:
            width = target_width
            if "left" in edges and "right" not in edges:
                left = right - width
            else:
                right = left + width
        else:
            width_change = abs(
                width - (self._initial_geometry[2] - self._initial_geometry[0])
            )
            height_change = abs(
                height
                - (self._initial_geometry[3] - self._initial_geometry[1])
            )
            if width_change >= height_change:
                height = target_height
                if "top" in edges and "bottom" not in edges:
                    top = bottom - height
                else:
                    bottom = top + height
            else:
                width = target_width
                if "left" in edges and "right" not in edges:
                    left = right - width
                else:
                    right = left + width

        return left, right, top, bottom

    def _apply_grid_snapping(
        self,
        edges: Set[str],
        left: float,
        right: float,
        top: float,
        bottom: float,
    ) -> tuple[float, float, float, float]:
        grid = getattr(self._view, "grid_settings", None)
        if not grid or not getattr(grid, "snap_to_grid", False):
            return left, right, top, bottom

        offset_x = self._view.canvas_offset_x
        offset_y = self._view.canvas_offset_y

        if "left" in edges or "top" in edges:
            snapped_left, snapped_top = snap_to_grid(
                grid, left + offset_x, top + offset_y, False
            )
            if "left" in edges:
                left = snapped_left - offset_x
            if "top" in edges:
                top = snapped_top - offset_y

        if "right" in edges or "bottom" in edges:
            snapped_right, snapped_bottom = snap_to_grid(
                grid, right + offset_x, bottom + offset_y, False
            )
            if "right" in edges:
                right = snapped_right - offset_x
            if "bottom" in edges:
                bottom = snapped_bottom - offset_y

        return left, right, top, bottom

    def _enforce_min_width(
        self, edges: Set[str], left: float, right: float
    ) -> tuple[float, float]:
        width = right - left
        if width >= self.MIN_WIDTH:
            return left, right
        if "left" in edges and "right" not in edges:
            left = right - self.MIN_WIDTH
        else:
            right = left + self.MIN_WIDTH
        return left, right

    def _enforce_min_height(
        self, edges: Set[str], top: float, bottom: float
    ) -> tuple[float, float]:
        height = bottom - top
        if height >= self.MIN_HEIGHT:
            return top, bottom
        if "top" in edges and "bottom" not in edges:
            top = bottom - self.MIN_HEIGHT
        else:
            bottom = top + self.MIN_HEIGHT
        return top, bottom

    def _open_delete_menu(self, event) -> None:
        menu = QMenu()
        delete_action = menu.addAction(self.tr("Delete"))
        chosen = menu.exec_(event.screenPos())
        if chosen != delete_action:
            return

        view = getattr(self, "_view", None)
        if view is not None:
            try:
                view._remove_text_item(self)
            except Exception:
                pass

    def _detect_anchor(self, local_pos: QPointF) -> Optional[str]:
        rect = self.rect()
        margin = self.BORDER_MARGIN
        left = abs(local_pos.x() - rect.left()) <= margin
        right = abs(local_pos.x() - rect.right()) <= margin
        top = abs(local_pos.y() - rect.top()) <= margin
        bottom = abs(local_pos.y() - rect.bottom()) <= margin

        if left and top:
            return "top-left"
        if right and top:
            return "top-right"
        if left and bottom:
            return "bottom-left"
        if right and bottom:
            return "bottom-right"
        if left:
            return "left"
        if right:
            return "right"
        if top:
            return "top"
        if bottom:
            return "bottom"
        return None

    @staticmethod
    def _cursor_for_anchor(anchor: Optional[str]):
        if anchor in {"top-left", "bottom-right"}:
            return Qt.CursorShape.SizeFDiagCursor
        if anchor in {"top-right", "bottom-left"}:
            return Qt.CursorShape.SizeBDiagCursor
        if anchor in {"left", "right"}:
            return Qt.CursorShape.SizeHorCursor
        if anchor in {"top", "bottom"}:
            return Qt.CursorShape.SizeVerCursor
        return None

    def _snap_position_if_needed(self, value):
        if not isinstance(value, QPointF):
            return value
        if self.current_tool != CanvasToolName.MOVE:
            return value

        grid = getattr(self._view, "grid_settings", None)
        if not grid or not getattr(grid, "snap_to_grid", False):
            return value

        abs_x = value.x() + self._view.canvas_offset_x
        abs_y = value.y() + self._view.canvas_offset_y
        snapped_x, snapped_y = snap_to_grid(grid, abs_x, abs_y, False)
        return QPointF(
            snapped_x - self._view.canvas_offset_x,
            snapped_y - self._view.canvas_offset_y,
        )
