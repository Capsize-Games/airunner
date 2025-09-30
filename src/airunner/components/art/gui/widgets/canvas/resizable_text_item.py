from PySide6.QtCore import (
    QPointF,
    Qt,
    QRectF,
)
from PySide6.QtGui import QColor, QBrush, QPen, QPainter
from PySide6.QtWidgets import (
    QGraphicsTextItem,
    QGraphicsRectItem,
)

from airunner.enums import CanvasToolName

# Forward reference for type hints
try:
    from airunner.components.art.gui.widgets.canvas.custom_view import (
        CustomGraphicsView,
    )
except Exception:
    CustomGraphicsView = object


class ResizableTextItem(QGraphicsRectItem):
    """A rectangular text area that contains a QGraphicsTextItem child.

    The rectangle clips its children so overflow is hidden. Supports resizing
    by dragging edges/corners and moves when MOVE tool is active.
    """

    HANDLE_SIZE = 8

    def __init__(self, view: "CustomGraphicsView", rect: QRectF):
        super().__init__(rect)
        self._view = view
        self.setFlag(QGraphicsRectItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsRectItem.ItemIsMovable, True)
        # Accept hover events to show resize cursors
        try:
            self.setAcceptHoverEvents(True)
        except Exception:
            pass
        # Clip children to this rect
        try:
            self.setFlag(QGraphicsRectItem.ItemClipsChildrenToShape, True)
        except Exception:
            # Some PySide6 versions don't expose this flag on QGraphicsRectItem;
            # fallback to setting the flag on the instance if possible.
            pass

        # Visual
        pen = QPen(QColor("white"))
        pen.setStyle(Qt.PenStyle.SolidLine)
        self.setPen(pen)

        # Create text child (custom class to forward border clicks)
        class _InnerTextItem(QGraphicsTextItem):
            def __init__(self, parent_area: "ResizableTextItem"):
                super().__init__(parent_area)
                self._parent_area = parent_area

            def mousePressEvent(self, event):
                # If click is near parent's border, forward to parent to begin resize
                try:
                    local = self._parent_area.mapFromScene(event.scenePos())
                    left, right, top, bottom = self._parent_area._is_on_border(
                        local, tol=self._parent_area.HANDLE_SIZE
                    )
                    if any((left, right, top, bottom)):
                        # Delegate to parent
                        self._parent_area.mousePressEvent(event)
                        return
                except Exception:
                    pass
                return QGraphicsTextItem.mousePressEvent(self, event)

        self.text_item = _InnerTextItem(self)
        self.text_item.setDefaultTextColor(QColor("white"))
        self.text_item.setFont(self._view._get_default_text_font())
        self.text_item.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.text_item.setPos(self.rect().topLeft())
        self.text_item.setTextWidth(self.rect().width())
        # Keep text child above the rect so it can be edited; mouse presses
        # on the text will be forwarded to parent when appropriate.
        self.text_item.setZValue(self.zValue() + 1)

        # Internal state for dragging/resizing
        # Increase handle size for better hit-testing/visibility
        self.HANDLE_SIZE = 12
        self._resizing = False
        self._moving = False
        self._resize_anchor = None
        self._press_pos = None
        self._initial_rect = QRectF(self.rect())

        # Create explicit handle items so they receive mouse events
        self._handles = {}

        class _HandleItem(QGraphicsRectItem):
            def __init__(self, parent_area: "ResizableTextItem", anchor: str):
                super().__init__(parent_area)
                self._parent_area = parent_area
                self._anchor = anchor
                self.setZValue(parent_area.zValue() + 100)
                # Make handles visible (white fill, black outline)
                self.setBrush(QBrush(QColor("white")))
                self.setPen(QPen(QColor("black")))
                # Only accept left-button clicks
                try:
                    self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
                except Exception:
                    pass
                # Ensure handles don't move/select themselves
                try:
                    self.setFlag(QGraphicsRectItem.ItemIsMovable, False)
                    self.setFlag(QGraphicsRectItem.ItemIsSelectable, False)
                except Exception:
                    pass
                try:
                    self.setAcceptHoverEvents(True)
                except Exception:
                    pass

            def hoverMoveEvent(self, event):
                # set appropriate cursor for this handle
                a = self._anchor
                if a in ("tl", "br"):
                    self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                elif a in ("tr", "bl"):
                    self.setCursor(Qt.CursorShape.SizeBDiagCursor)
                elif a in ("l", "r"):
                    self.setCursor(Qt.CursorShape.SizeHorCursor)
                else:
                    self.setCursor(Qt.CursorShape.SizeVerCursor)
                QGraphicsRectItem.hoverMoveEvent(self, event)

            def mousePressEvent(self, event):
                # Start a resize operation on the parent
                try:
                    # Grab the mouse so subsequent move events are delivered
                    try:
                        self.grabMouse()
                    except Exception:
                        pass
                    self._parent_area._start_resize(
                        self._anchor, event.scenePos()
                    )
                    event.accept()
                except Exception:
                    QGraphicsRectItem.mousePressEvent(self, event)

            def mouseMoveEvent(self, event):
                try:
                    self._parent_area._do_resize(event.scenePos())
                    event.accept()
                except Exception:
                    QGraphicsRectItem.mouseMoveEvent(self, event)

            def mouseReleaseEvent(self, event):
                try:
                    self._parent_area._end_resize(event.scenePos())
                    try:
                        self.ungrabMouse()
                    except Exception:
                        pass
                    event.accept()
                except Exception:
                    QGraphicsRectItem.mouseReleaseEvent(self, event)

        # Create handles for corners and edges
        anchors = ["tl", "tr", "bl", "br", "t", "b", "l", "r"]
        for a in anchors:
            h = _HandleItem(self, a)
            self._handles[a] = h
        # Position handles according to current rect
        self._reposition_handles()

    @property
    def current_tool(self):
        try:
            return self._view.current_tool
        except Exception:
            return None

    def _is_on_border(self, pos: QPointF, tol: int = 6):
        r = self.rect()
        x, y = pos.x(), pos.y()
        left = abs(x - r.left()) <= tol
        right = abs(x - r.right()) <= tol
        top = abs(y - r.top()) <= tol
        bottom = abs(y - r.bottom()) <= tol
        return left, right, top, bottom

    def _reposition_handles(self):
        """Place handle rects in local coordinates around the current rect."""
        r = self.rect()
        hs = self.HANDLE_SIZE
        coords = {
            "tl": (r.left(), r.top()),
            "tr": (r.right(), r.top()),
            "bl": (r.left(), r.bottom()),
            "br": (r.right(), r.bottom()),
            "t": ((r.left() + r.right()) / 2, r.top()),
            "b": ((r.left() + r.right()) / 2, r.bottom()),
            "l": (r.left(), (r.top() + r.bottom()) / 2),
            "r": (r.right(), (r.top() + r.bottom()) / 2),
        }
        for k, h in self._handles.items():
            cx, cy = coords[k]
            h.setRect(cx - hs / 2, cy - hs / 2, hs, hs)

    def _start_resize(self, anchor: str, scene_pos: QPointF):
        # Delegate resizing to the view so mouse move events are handled
        # reliably even if the handle doesn't retain the grab in some
        # environments. The view will call back into the area's _do_resize
        # and _end_resize methods as needed.
        try:
            # disable text interaction while resizing to avoid selection
            try:
                self.text_item.setTextInteractionFlags(Qt.NoTextInteraction)
            except Exception:
                pass
            if hasattr(self._view, "_begin_area_resize"):
                self._view._begin_area_resize(self, anchor, scene_pos)
                return
        except Exception:
            pass
        # Fallback to local behavior
        self._resizing = True
        self._resize_anchor = anchor
        self._press_pos = scene_pos
        self._initial_rect = QRectF(self.rect())

    def _do_resize(self, scene_pos: QPointF):
        # Prefer view-driven resize if active
        try:
            if (
                hasattr(self._view, "_do_area_resize")
                and getattr(self._view, "_active_resizer_area", None) is self
            ):
                # view handles calling back into this area's _do_resize_local
                return
        except Exception:
            pass
        # Fallback local resize behavior
        if not self._resizing or not self._press_pos:
            return
        delta = scene_pos - self._press_pos
        r = QRectF(self._initial_rect)
        a = self._resize_anchor
        if "l" in a:
            r.setLeft(r.left() + delta.x())
        if "r" in a:
            r.setRight(r.right() + delta.x())
        if "t" in a:
            r.setTop(r.top() + delta.y())
        if "b" in a:
            r.setBottom(r.bottom() + delta.y())
        min_w, min_h = 20, 20
        if r.width() < min_w:
            r.setRight(r.left() + min_w)
        if r.height() < min_h:
            r.setBottom(r.top() + min_h)
        self.setRect(r)
        self.text_item.setPos(r.topLeft())
        self.text_item.setTextWidth(r.width())
        self._reposition_handles()

    def _end_resize(self, scene_pos: QPointF):
        # If the view is coordinating the resize, let it finish. Otherwise
        # finish locally.
        try:
            if (
                hasattr(self._view, "_end_area_resize")
                and getattr(self._view, "_active_resizer_area", None) is self
            ):
                return
        except Exception:
            pass
        if not self._resizing:
            return
        self._resizing = False
        # re-enable text interaction
        try:
            self.text_item.setTextInteractionFlags(Qt.TextEditorInteraction)
        except Exception:
            pass
        # persist
        try:
            self._view._save_text_items_to_db()
        except Exception:
            pass

    def hoverMoveEvent(self, event):
        # Change the cursor when hovering near borders/corners
        local = self.mapFromScene(event.scenePos())
        left, right, top, bottom = self._is_on_border(
            local, tol=self.HANDLE_SIZE
        )
        cursor = None
        if left and top or right and bottom:
            cursor = Qt.CursorShape.SizeFDiagCursor
        elif left and bottom or right and top:
            cursor = Qt.CursorShape.SizeBDiagCursor
        elif left or right:
            cursor = Qt.CursorShape.SizeHorCursor
        elif top or bottom:
            cursor = Qt.CursorShape.SizeVerCursor
        else:
            # Default depending on tool
            if self.current_tool is CanvasToolName.MOVE:
                cursor = Qt.CursorShape.OpenHandCursor
            else:
                cursor = Qt.CursorShape.IBeamCursor

        # Only set when changed to avoid thrash
        try:
            self.setCursor(cursor)
        except Exception:
            pass
        QGraphicsRectItem.hoverMoveEvent(self, event)

    def hoverLeaveEvent(self, event):
        # reset cursor to default when leaving
        try:
            # Let the view set its cursor based on current tool
            self.unsetCursor()
        except Exception:
            pass
        QGraphicsRectItem.hoverLeaveEvent(self, event)

    def paint(self, painter: QPainter, option, widget=None):
        # Default rectangle paint
        QGraphicsRectItem.paint(self, painter, option, widget)
        # Draw small handles when selected
        if not self.isSelected():
            return
        r = self.rect()
        hs = self.HANDLE_SIZE
        handles = [
            QRectF(r.left() - hs / 2, r.top() - hs / 2, hs, hs),
            QRectF(r.right() - hs / 2, r.top() - hs / 2, hs, hs),
            QRectF(r.left() - hs / 2, r.bottom() - hs / 2, hs, hs),
            QRectF(r.right() - hs / 2, r.bottom() - hs / 2, hs, hs),
        ]
        painter.save()
        painter.setPen(QPen(QColor("white")))
        painter.setBrush(QBrush(QColor("white")))
        for h in handles:
            painter.drawRect(h)
        painter.restore()

    def mousePressEvent(self, event):
        # If move tool is active, allow moving via normal mechanism
        if (
            self.current_tool is CanvasToolName.MOVE
            and event.button() == Qt.MouseButton.LeftButton
        ):
            # Record move start
            self._moving = True
            self._press_pos = event.scenePos()
            self._initial_rect = QRectF(self.rect())
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            # Map to local rect coordinates
            local = self.mapFromScene(event.scenePos())
            left, right, top, bottom = self._is_on_border(local)
            if any((left, right, top, bottom)):
                # Begin resize; record anchor
                self._resizing = True
                self._press_pos = event.scenePos()
                self._initial_rect = QRectF(self.rect())
                # store which edges are being dragged
                self._resize_anchor = (left, right, top, bottom)
                event.accept()
                return

        # Default: forward to child text item (for editing)
        QGraphicsRectItem.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if self._resizing and self._press_pos is not None:
            # compute delta in scene coords and adjust rect
            delta = event.scenePos() - self._press_pos
            r = QRectF(self._initial_rect)
            left, right, top, bottom = self._resize_anchor
            if left:
                r.setLeft(r.left() + delta.x())
            if right:
                r.setRight(r.right() + delta.x())
            if top:
                r.setTop(r.top() + delta.y())
            if bottom:
                r.setBottom(r.bottom() + delta.y())
            # enforce minimum size
            min_w, min_h = 20, 20
            if r.width() < min_w:
                r.setRight(r.left() + min_w)
            if r.height() < min_h:
                r.setBottom(r.top() + min_h)
            self.setRect(r)
            self.text_item.setPos(r.topLeft())
            self.text_item.setTextWidth(r.width())
            event.accept()
            return

        if self._moving and self._press_pos is not None:
            delta = event.scenePos() - self._press_pos
            self.setPos(self.pos() + delta)
            self._press_pos = event.scenePos()
            event.accept()
            return

        QGraphicsRectItem.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        if self._resizing:
            self._resizing = False
            # Persist changes
            try:
                self._view._save_text_items_to_db()
            except Exception:
                pass
            event.accept()
            return
        if self._moving:
            self._moving = False
            try:
                self._view._save_text_items_to_db()
            except Exception:
                pass
            event.accept()
            return

        QGraphicsRectItem.mouseReleaseEvent(self, event)

    def setText(self, text: str):
        self.text_item.setPlainText(text)

    def to_persist_dict(self):
        # return a dict suitable for JSON persistence
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
