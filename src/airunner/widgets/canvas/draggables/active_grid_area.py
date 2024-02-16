from PIL.ImageQt import QImage

from PyQt6.QtCore import QRect
from PyQt6.QtGui import QBrush, QColor, QPen, QPixmap, QPainter
from PyQt6.QtWidgets import QGraphicsItem

from airunner.enums import SignalCode, CanvasToolName
from airunner.service_locator import ServiceLocator
from airunner.widgets.canvas.draggables.draggable_pixmap import DraggablePixmap


class ActiveGridArea(DraggablePixmap):
    @property
    def rect(self):
        settings = ServiceLocator.get("get_settings")()
        active_grid_settings = settings["active_grid_settings"]
        return QRect(
            active_grid_settings["pos_x"],
            active_grid_settings["pos_y"],
            active_grid_settings["width"],
            active_grid_settings["height"]
        )

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
        self.render_fill()

        super().__init__(self.pixmap)

        painter = self.draw_border()
        super().paint(painter, None, None)

        self.update_position()
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable,
            True
        )
        self.register(
            SignalCode.ACTIVE_GRID_SETTINGS_CHANGED_SIGNAL,
            self.render_fill
        )

    def update_position(self):
        self.setPos(
            min(self.rect.x(), self.rect.x() + self.rect.width()),
            min(self.rect.y(), self.rect.y() + self.rect.height())
        )

    def render_fill(self):
        settings = ServiceLocator.get("get_settings")()

        if (
            self._current_width != self.rect.width() or
            self._current_height != self.rect.height() or
            self._do_render_fill != settings["active_grid_settings"]["render_fill"] or
            self._active_grid_settings_enabled != settings["active_grid_settings"]["enabled"]
        ):
            self._do_render_fill = settings["active_grid_settings"]["render_fill"]
            self._current_width = self.rect.width()
            self._current_height = self.rect.height()
            self._active_grid_settings_enabled = settings["active_grid_settings"]["enabled"]

            active_grid_settings = settings["active_grid_settings"]
            render_fill = active_grid_settings["render_fill"] and active_grid_settings["enabled"]

            fill_color = self.get_fill_color()

            width = abs(self.rect.width())
            height = abs(self.rect.height())

            if not self.image:
                self.image = QImage(
                    width,
                    height,
                    QImage.Format.Format_ARGB32
                )
            else:
                self.image = self.image.scaled(
                    width,
                    height
                )

            if render_fill:
                self.image.fill(fill_color)
            else:
                self.image.fill(QColor(0, 0, 0, 1))
            self.pixmap = QPixmap.fromImage(self.image)

    def get_fill_color(self) -> QColor:
        settings = ServiceLocator.get("get_settings")()
        render_fill = settings["active_grid_settings"]["render_fill"]
        if render_fill:
            fill_color = settings["generator_settings"]["active_grid_fill_color"]
            fill_color = QColor(fill_color)
            fill_opacity = settings["active_grid_settings"]["fill_opacity"]
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
            painter = QPainter()

        settings = ServiceLocator.get("get_settings")()

        if settings["active_grid_settings"]["enabled"]:
            render_border = settings["active_grid_settings"]["render_border"]
            line_width = settings["grid_settings"]["line_width"]

            self._draggable_rect = QRect(
                0,
                0,
                abs(self.rect.width()),
                abs(self.rect.height())
            )
            border_color = QColor(settings["generator_settings"]["active_grid_border_color"])
            border_color.setAlpha(settings["active_grid_settings"]["border_opacity"])
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
        #super().paint(painter, option, widget)

    def toggle_render_border(self, value):
        pass

    def change_border_opacity(self, value):
        pass

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)

    @property
    def settings(self):
        return ServiceLocator.get("get_settings")()

    @settings.setter
    def settings(self, value):
        ServiceLocator.get("set_settings")(value)

    def setPos(self, x, y):
        super().setPos(x, y)
        settings = ServiceLocator.get("get_settings")()
        tool = settings["current_tool"]
        if tool is CanvasToolName.ACTIVE_GRID_AREA:
            active_grid_settings = settings["active_grid_settings"]
            active_grid_settings["pos_x"] = x
            active_grid_settings["pos_y"] = y
            self.settings = settings
