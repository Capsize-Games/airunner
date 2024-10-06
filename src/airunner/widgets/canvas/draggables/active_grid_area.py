from PIL.ImageQt import QImage

from PySide6.QtCore import QRect, QPoint
from PySide6.QtGui import QBrush, QColor, QPen, QPixmap, QPainter, Qt
from PySide6.QtWidgets import QGraphicsItem

from airunner.enums import SignalCode, CanvasToolName
from airunner.widgets.canvas.draggables.draggable_pixmap import DraggablePixmap


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
        self._draggable_rect: QRect = None
        self._border_pen: QPen = None
        self._outer_border_pen: QPen = None
        self._border_color: QColor = None
        self._border_brush: QBrush = None

        super().__init__(QPixmap())
        self.render_fill()

        painter = self.draw_border()
        super().paint(painter, None, None)

        self.snap_to_grid(
            x=min(self.rect.x(), self.rect.x() + self.rect.width()),
            y=min(self.rect.y(), self.rect.y() + self.rect.height()),
            save=True
        )
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable,
            True
        )
        self.register(
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL,
            self.render_fill
        )

    def update_position(self, x: int, y: int, save: bool = True):
        self.setPos(QPoint(x, y))
        if save:
            self.update_active_grid_settings("pos_x", x)
            self.update_active_grid_settings("pos_y", y)

    @property
    def rect(self):
        return QRect(
            self.active_grid_settings.pos_x,
            self.active_grid_settings.pos_y,
            self.application_settings.working_width,
            self.application_settings.working_height
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

        fill_color = self.get_fill_color() if self._do_render_fill else QColor(0, 0, 0, 1)
        self.image.fill(fill_color)
        pixmap = QPixmap.fromImage(self.image)
        self.setPixmap(pixmap)

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

    def change_fill_opacity(self, value):
        self.update_selection_fill()

    def update_selection_fill(self):
        self.pixmap.fill(self.get_fill_color())

    def draw_border(self, painter: QPainter = None):
        if painter is None:
            painter = QPainter(self.pixmap)

        if self.active_grid_settings.enabled:
            render_border = self.active_grid_settings.render_border
            line_width = self.grid_settings.line_width

            self._draggable_rect = QRect(
                0,
                0,
                abs(self.rect.width()),
                abs(self.rect.height())
            )
            border_color = QColor(self.active_grid_settings.border_color)
            border_color.setAlpha(self.active_grid_settings.border_opacity)
            self._border_pen = QPen(
                border_color,
                line_width
            )
            self._outer_border_pen = QPen(
                border_color,
                line_width + 1
            )
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

    mouse_press_pos = None

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.mouse_press_pos = event.pos()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if self.mouse_press_pos and self.current_tool is CanvasToolName.ACTIVE_GRID_AREA and (
            self.mouse_press_pos.x() != event.pos().x() or
            self.mouse_press_pos.y() != event.pos().y()
        ):
            self.emit_signal(SignalCode.ACTIVE_GRID_AREA_MOVED_SIGNAL)
            self.emit_signal(SignalCode.GENERATE_MASK)
        self.mouse_press_pos = None

    def mouseMoveEvent(self, event):
        if self.current_tool not in [
            CanvasToolName.ACTIVE_GRID_AREA,
        ]:
            return
        super().mouseMoveEvent(event)
