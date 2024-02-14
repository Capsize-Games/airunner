from typing import Optional

from PIL.ImageQt import QImage

from PyQt6.QtCore import QRect, QPoint
from PyQt6.QtGui import QBrush, QColor, QPen, QPixmap, QPainter
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsPixmapItem

from airunner.enums import SignalCode, CanvasToolName
from airunner.mediator_mixin import MediatorMixin
from airunner.service_locator import ServiceLocator

class DraggablePixmap(
    QGraphicsPixmapItem,
    MediatorMixin
):
    def __init__(self, pixmap):
        super().__init__(pixmap)
        MediatorMixin.__init__(self)
        self.pixmap = pixmap
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.last_pos = QPoint(0, 0)

    def snap_to_grid(self):
        settings = ServiceLocator.get("get_settings")()
        cell_size = settings["grid_settings"]["cell_size"]
        x = round(self.x() / cell_size) * cell_size
        y = round(self.y() / cell_size) * cell_size
        x += self.last_pos.x()
        y += self.last_pos.y()
        self.setPos(x, y)

    def mouseMoveEvent(self, event):
        settings = ServiceLocator.get("get_settings")()
        tool = settings["current_tool"]
        if tool is not CanvasToolName.ACTIVE_GRID_AREA:
            return
        super().mouseMoveEvent(event)
        self.snap_to_grid()

    def mouseReleaseEvent(self, event):
        settings = ServiceLocator.get("get_settings")()
        tool = settings["current_tool"]
        if tool is CanvasToolName.ACTIVE_GRID_AREA:
            self.snap_to_grid()
        super().mouseReleaseEvent(event)

    def paint(self, painter: QPainter, option, widget=None):
        painter.drawPixmap(self.pixmap.rect(), self.pixmap)


class LayerImageItem(DraggablePixmap):
    def __init__(self, pixmap, layer_image_data):
        self.layer_image_data = layer_image_data
        super().__init__(pixmap)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        pos = self.pos()
        self.layer_image_data["pos_x"] = pos.x()
        self.layer_image_data["pos_y"] = pos.y()


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
        self.active_grid_area_color = None
        self.image = None
        self._current_width = 0
        self._current_height = 0
        self._render_border: bool = False
        self._line_width: int = 1
        self._do_draw = True
        self._draggable_rect: QRect = Optional[None]
        self._border_pen: QPen = Optional[None]
        self._outter_border_pen: QPen = Optional[None]
        self._border_color: QColor = Optional[None]
        self._border_brush: QBrush = Optional[None]
        self.update_draggable_settings()

        super().__init__(self.pixmap)

        self.update_position()
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable,
            True
        )
        self.register(
            SignalCode.ACTIVE_GRID_SETTINGS_CHANGED_SIGNAL,
            self.update_draggable_settings
        )

    def update_position(self):
        self.setPos(
            min(self.rect.x(), self.rect.x() + self.rect.width()),
            min(self.rect.y(), self.rect.y() + self.rect.height())
        )

    def update_draggable_settings(self):
        if self._current_width != self.rect.width() or self._current_height != self.rect.height():
            self._current_width = self.rect.width()
            self._current_height = self.rect.height()

            settings = ServiceLocator.get("get_settings")()
            generator_settings = settings["generator_settings"]
            border_color = generator_settings["active_grid_border_color"]

            active_grid_settings = settings["active_grid_settings"]
            render_border = active_grid_settings["render_border"]
            render_fill = active_grid_settings["render_fill"]
            border_opacity = active_grid_settings["border_opacity"]

            if render_border:
                border_color = QColor(border_color)
                border_color.setAlpha(border_opacity)
                self.active_grid_area_color = border_color

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

    def paint(self, painter: QPainter, option, widget=None):
        settings = ServiceLocator.get("get_settings")()
        render_border = settings["active_grid_settings"]["render_border"]
        line_width = settings["grid_settings"]["line_width"]

        if render_border != self._render_border or line_width != self._line_width or self._do_draw:
            self._do_draw = False
            self._render_border = render_border
            self._line_width = line_width
            self.update_draggable_settings()
            self._draggable_rect = QRect(
                0,
                0,
                abs(self.rect.width()),
                abs(self.rect.height())
            )
            self._border_pen = self._border_pen = QPen(
                self.active_grid_area_color,
                line_width
            )
            self._outter_border_pen = QPen(
                self.active_grid_area_color,
                line_width + 1
            )
            self._border_color = QColor(0, 0, 0, 0)
            self._border_brush = QBrush(self._border_color)

        if render_border:
            painter.setPen(self._border_pen)
            painter.setBrush(self._border_brush)
            painter.drawRect(self._draggable_rect)
            painter.setPen(self._outter_border_pen)
            painter.drawRect(self._draggable_rect)

        super().paint(painter, option, widget)

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
