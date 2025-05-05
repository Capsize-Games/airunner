from typing import Optional

from PIL.ImageQt import QImage

from PySide6.QtCore import QRect, QPoint, QPointF
from PySide6.QtGui import QBrush, QColor, QPen, QPixmap, QPainter, Qt
from PySide6.QtWidgets import QGraphicsItem

from airunner.enums import SignalCode, CanvasToolName
from airunner.gui.widgets.canvas.draggables.draggable_pixmap import (
    DraggablePixmap,
)
from airunner.utils.application.snap_to_grid import snap_to_grid


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

        super().__init__(QPixmap())
        self.render_fill()
        painter = self.draw_border()
        super().paint(painter, None, None)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.register(
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL, self.render_fill
        )

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

        if not self.image:
            self.image = QImage(width, height, QImage.Format.Format_ARGB32)
        else:
            self.image = self.image.scaled(width, height)

        fill_color = (
            self.get_fill_color()
            if self._do_render_fill
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
        # Handle drag initiation
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self.current_tool is CanvasToolName.ACTIVE_GRID_AREA
        ):
            # Store the initial scene position of the mouse
            self.initial_mouse_scene_pos = event.scenePos()

            # Store current absolute position from settings
            abs_x = self.active_grid_settings.pos_x
            abs_y = self.active_grid_settings.pos_y
            if abs_x is None:
                abs_x = 0
            if abs_y is None:
                abs_y = 0
            self.initial_item_abs_pos = QPointF(abs_x, abs_y)

            # Also store item-relative position for release check
            self.mouse_press_pos = event.pos()
            event.accept()
        else:
            # Not dragging this item, let base class handle
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # Only handle drag if we initiated one on this item
        if (
            self.current_tool is CanvasToolName.ACTIVE_GRID_AREA
            and self.initial_mouse_scene_pos is not None
        ):
            # Calculate delta from initial press in scene coordinates
            delta = event.scenePos() - self.initial_mouse_scene_pos

            # Calculate new proposed absolute position
            proposed_abs_x = self.initial_item_abs_pos.x() + delta.x()
            proposed_abs_y = self.initial_item_abs_pos.y() + delta.y()

            # Apply grid snapping
            snapped_abs_x, snapped_abs_y = snap_to_grid(
                self.grid_settings, proposed_abs_x, proposed_abs_y
            )

            # During drag, only update display position - we'll save settings on mouseRelease
            try:
                view = self.scene().views()[0]
                canvas_offset = view.canvas_offset
            except (AttributeError, IndexError):
                canvas_offset = QPointF(0, 0)

            # Set visual position directly for smooth performance
            display_x = snapped_abs_x - canvas_offset.x()
            display_y = snapped_abs_y - canvas_offset.y()
            self.setPos(display_x, display_y)

            # Store current snapped position for release handler to use
            self._current_snapped_pos = (
                int(snapped_abs_x),
                int(snapped_abs_y),
            )

            # Accept the event to prevent further processing
            event.accept()
        else:
            # Not our drag, let base class handle
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if (
            self.current_tool is CanvasToolName.ACTIVE_GRID_AREA
            and self.initial_mouse_scene_pos is not None
        ):
            # Reset drag tracking
            has_moved = False
            if self.mouse_press_pos:
                has_moved = (
                    self.mouse_press_pos.x() != event.pos().x()
                    or self.mouse_press_pos.y() != event.pos().y()
                )

            self.initial_mouse_scene_pos = None
            self.initial_item_abs_pos = None
            self.mouse_press_pos = None

            # Emit signal if we moved
            if has_moved:
                self.api.art.canvas.generate_mask()
                self.api.art.active_grid_area_updated()

                # Save the snapped absolute position
                if (
                    int(self._current_snapped_pos[0])
                    != self.active_grid_settings.pos_x
                    or int(self._current_snapped_pos[1])
                    != self.active_grid_settings.pos_y
                ):
                    # Update DB settings
                    self.update_active_grid_settings(
                        "pos_x", int(self._current_snapped_pos[0])
                    )
                    self.update_active_grid_settings(
                        "pos_y", int(self._current_snapped_pos[1])
                    )

            # Accept the event
            event.accept()
        else:
            # Not our drag, let base class handle
            super().mouseReleaseEvent(event)
