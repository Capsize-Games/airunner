from typing import Optional

from PIL.ImageQt import QImage

from PySide6.QtCore import QRect, QPointF
from PySide6.QtGui import QBrush, QColor, QPen, QPainter, Qt
from PySide6.QtWidgets import QGraphicsItem

from airunner.enums import SignalCode, CanvasToolName
from airunner.components.art.gui.widgets.canvas.draggables.draggable_pixmap import (
    DraggablePixmap,
)
from airunner.components.art.utils.canvas_position_manager import (
    CanvasPositionManager,
    ViewState,
)


class ActiveGridArea(DraggablePixmap):
    def __init__(self):
        self.image = None
        self._current_width = 0
        self._current_height = 0
        self._render_border: bool = False
        self._line_width: int = 1
        self._do_draw = True
        self._do_render_fill = False
        self._active_grid_settings_enabled = False
        self._draggable_rect: Optional[QRect] = None
        self._border_pen: Optional[QPen] = None
        self._outer_border_pen: Optional[QPen] = None
        self._border_color: Optional[QColor] = None
        self._border_brush: Optional[QBrush] = None
        # For drag tracking
        self.initial_mouse_scene_pos = None
        self.initial_item_abs_pos = None
        self.mouse_press_pos = None
        self._current_snapped_pos: tuple[int, int] = (0, 0)

        super().__init__(None, use_layer_context=False)
        self.render_fill()
        painter = self.draw_border()
        super().paint(painter, None, None)
        # Don't use ItemIsMovable - we handle positioning manually
        # ItemIsMovable causes Qt to apply its own position changes which
        # conflicts with our manual positioning in mouseMoveEvent/mouseReleaseEvent
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.register(
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL, self.render_fill
        )
        self.register(
            SignalCode.APPLICATION_TOOL_CHANGED_SIGNAL, self.on_tool_changed
        )
        self.setZValue(10000)
        # Update mouse acceptance based on current tool
        self.update_mouse_acceptance()

    def on_tool_changed(self, data=None):
        """Called when the tool changes - update whether we accept mouse events."""
        self.update_mouse_acceptance()

    def update_mouse_acceptance(self):
        """Enable/disable mouse events based on current tool."""
        is_active_tool = self.current_tool == CanvasToolName.ACTIVE_GRID_AREA
        if is_active_tool:
            self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        else:
            self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

    @property
    def rect(self):
        pos = self.active_grid_settings.pos
        return QRect(
            pos[0],
            pos[1],
            self.application_settings.working_width,
            self.application_settings.working_height,
        )

    def render_fill(self):
        self._current_width = self.rect.width()
        self._current_height = self.rect.height()
        self._do_render_fill = self.active_grid_settings.render_fill
        self._active_grid_settings_enabled = self.active_grid_settings.enabled

        width = abs(self.rect.width())
        height = abs(self.rect.height())

        if not self.image or self.image.isNull():
            self.image = QImage(width, height, QImage.Format.Format_ARGB32)
        else:
            # Guard against null image scaling
            if width > 0 and height > 0:
                self.image = self.image.scaled(width, height)
            else:
                self.image = QImage(width, height, QImage.Format.Format_ARGB32)

        fill_color = (
            self.get_fill_color()
            if self._do_render_fill and self._active_grid_settings_enabled
            else QColor(0, 0, 0, 1)
        )
        self.image.fill(fill_color)
        self.updateImage(self.image)

    def get_fill_color(self) -> QColor:
        render_fill = self.active_grid_settings.render_fill
        if render_fill:
            fill_color = self.active_grid_settings.fill_color
            fill_color = QColor(fill_color)
            fill_opacity = self.active_grid_settings.fill_opacity
            fill_opacity = max(1, fill_opacity)
            fill_color.setAlpha(fill_opacity)
        else:
            fill_color = QColor(0, 0, 0, 1)
        return fill_color

    def toggle_render_fill(self, _render_fill):
        self.update_selection_fill()

    def change_fill_opacity(self, _value):
        self.update_selection_fill()

    def update_selection_fill(self):
        self.pixmap.fill(self.get_fill_color())

    def draw_border(self, painter: QPainter = None) -> QPainter:
        if painter is None:
            painter = QPainter()

        if self.active_grid_settings.enabled:
            render_border = self.active_grid_settings.render_border
            line_width = self.grid_settings.line_width

            self._draggable_rect = QRect(
                0, 0, abs(self.rect.width()), abs(self.rect.height())
            )
            border_color = QColor(self.active_grid_settings.border_color)
            border_color.setAlpha(self.active_grid_settings.border_opacity)
            self._border_pen = QPen(border_color, line_width)
            self._outer_border_pen = QPen(border_color, line_width + 1)
            self._border_color = QColor(0, 0, 0, 0)
            self._border_brush = QBrush(self._border_color)

            if render_border:
                painter.setPen(self._border_pen)
                painter.setBrush(self._border_brush)
                painter.drawRect(self._draggable_rect)
                painter.setPen(self._outer_border_pen)
                painter.drawRect(self._draggable_rect)
        return painter

    def paint(self, painter: QPainter, option, widget=None):
        painter = self.draw_border(painter)
        super().paint(painter, option, widget)

    def toggle_render_border(self, value):
        pass

    def change_border_opacity(self, value):
        pass

    def mousePressEvent(self, event):
        if self.current_tool != CanvasToolName.ACTIVE_GRID_AREA:
            super().mousePressEvent(event)
            return

        view = self.scene().views()[0]

        if hasattr(self.scene(), "is_dragging"):
            self.scene().is_dragging = True

        # Create ViewState from view
        view_state = ViewState(
            canvas_offset=QPointF(
                getattr(view, "canvas_offset_x", 0.0),
                getattr(view, "canvas_offset_y", 0.0),
            ),
            grid_compensation=getattr(view, "grid_compensation_offset", QPointF(0.0, 0.0)),
        )

        # Use manager to convert display position to absolute position
        manager = CanvasPositionManager()
        self.drag_start_abs_pos = manager.display_to_absolute(
            self.pos(), view_state
        )
        self.drag_start_mouse_pos = event.scenePos()
        self.drag_start_display_pos = self.pos()

        # Don't call super().mousePressEvent(event) - it starts Qt's built-in drag
        event.accept()

    def mouseMoveEvent(self, event):
        # Only respond to drag when ACTIVE_GRID_AREA tool is active
        if self.current_tool != CanvasToolName.ACTIVE_GRID_AREA:
            super().mouseMoveEvent(event)
            return

        view = self.scene().views()[0]

        # Create ViewState from view
        view_state = ViewState(
            canvas_offset=QPointF(
                getattr(view, "canvas_offset_x", 0.0),
                getattr(view, "canvas_offset_y", 0.0),
            ),
            grid_compensation=getattr(view, "grid_compensation_offset", QPointF(0.0, 0.0)),
        )

        # Use manager to calculate drag position
        manager = CanvasPositionManager()
        mouse_delta = event.scenePos() - self.drag_start_mouse_pos

        # Enable snap-to-grid during drag if enabled
        snap_enabled = self.grid_settings.snap_to_grid
        cell_size = self.grid_settings.cell_size if snap_enabled else 0
        center_pos = getattr(view, "center_pos", QPointF(0, 0))

        _, new_display_pos = manager.calculate_drag_position(
            self.drag_start_abs_pos,
            mouse_delta,
            view_state,
            snap_enabled=snap_enabled,
            cell_size=cell_size,
            grid_origin=center_pos,
        )

        self.setPos(new_display_pos)
        self.drag_final_display_pos = new_display_pos
        event.accept()

    def mouseReleaseEvent(self, event):
        if self.current_tool != CanvasToolName.ACTIVE_GRID_AREA:
            super().mouseReleaseEvent(event)
            return

        view = self.scene().views()[0]

        if hasattr(self, "drag_final_display_pos"):
            current_display_pos = self.drag_final_display_pos
        else:
            current_display_pos = self.pos()

        # Create ViewState from view
        view_state = ViewState(
            canvas_offset=QPointF(
                getattr(view, "canvas_offset_x", 0.0),
                getattr(view, "canvas_offset_y", 0.0),
            ),
            grid_compensation=getattr(view, "grid_compensation_offset", QPointF(0.0, 0.0)),
        )

        manager = CanvasPositionManager()

        # Convert current display position to absolute position
        abs_pos = manager.display_to_absolute(current_display_pos, view_state)

        # Snap to grid in absolute space if enabled
        if self.grid_settings.snap_to_grid:
            center_pos = getattr(view, "center_pos", QPointF(0, 0))
            abs_pos = manager.snap_to_grid(
                abs_pos, self.grid_settings.cell_size, grid_origin=center_pos
            )

            # Update display position to snapped absolute position
            display_pos = manager.absolute_to_display(abs_pos, view_state)
            self.setPos(display_pos)

        self.save_position(abs_pos)
        event.accept()

        # Clear drag flag after delay to ensure signal processing completes
        from PySide6.QtCore import QTimer

        def clear_flag():
            if hasattr(self.scene(), "is_dragging"):
                self.scene().is_dragging = False

        QTimer.singleShot(500, clear_flag)

    def save_position(self, abs_pos: QPointF):
        """Save the absolute position to database."""
        # Only save if position changed
        if (
            int(abs_pos.x()) != self.active_grid_settings.pos_x
            or int(abs_pos.y()) != self.active_grid_settings.pos_y
        ):
            # Update DB settings - this will also invalidate the cache
            # so subsequent reads get the new values
            self.update_active_grid_settings(
                pos_x=int(abs_pos.x()),
                pos_y=int(abs_pos.y()),
            )

            # Verify the update worked by reading back from DB
            fresh_settings = self.active_grid_settings

            # Keep the view's center position in sync so startup alignment
            # logic preserves the manually positioned grid on next launch.
            view = None
            if self.scene() and self.scene().views():
                view = self.scene().views()[0]

            if view is not None:
                new_center = QPointF(
                    float(fresh_settings.pos_x), float(fresh_settings.pos_y)
                )
                view.center_pos = new_center
                view.save_canvas_offset()

            # Trigger mask regeneration and update signal
            self.api.art.canvas.generate_mask()
