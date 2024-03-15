from PySide6.QtCore import QPoint
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QGraphicsItem, QGraphicsPixmapItem

from airunner.enums import CanvasToolName
from airunner.mediator_mixin import MediatorMixin
from airunner.service_locator import ServiceLocator
from airunner.utils import snap_to_grid
from airunner.windows.main.settings_mixin import SettingsMixin


class DraggablePixmap(
    QGraphicsPixmapItem,
    MediatorMixin,
    SettingsMixin
):
    def __init__(self, pixmap):
        super().__init__(pixmap)
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)
        self.pixmap = pixmap
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.last_pos = QPoint(0, 0)

    @property
    def current_tool(self):
        settings = ServiceLocator.get("get_settings")()
        tool = settings["current_tool"]
        return tool

    def mouseMoveEvent(self, event):
        if self.current_tool is not CanvasToolName.ACTIVE_GRID_AREA:
            return
        super().mouseMoveEvent(event)
        self.snap_to_grid()

    def mouseReleaseEvent(self, event):
        if self.current_tool is CanvasToolName.ACTIVE_GRID_AREA:
            self.snap_to_grid(save=True)
        super().mouseReleaseEvent(event)

    def snap_to_grid(self, save=False):
        x, y = snap_to_grid(
            int(self.x()),
            int(self.y()),
            False
        )
        x += self.last_pos.x()
        y += self.last_pos.y()
        self.setPos(x, y, save)

    def setPos(self, x, y, save=False):
        super().setPos(x, y)
        if save:
            if self.current_tool is CanvasToolName.ACTIVE_GRID_AREA:
                settings = ServiceLocator.get("get_settings")()
                active_grid_settings = settings["active_grid_settings"]
                active_grid_settings["pos_x"] = x
                active_grid_settings["pos_y"] = y
                self.settings = settings

    def paint(self, painter: QPainter, option, widget=None):
        painter.drawPixmap(self.pixmap.rect(), self.pixmap)
