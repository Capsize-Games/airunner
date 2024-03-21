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
        self.save = False

    @property
    def current_tool(self):
        settings = self.settings
        tool = settings["current_tool"]
        return tool

    def mouseMoveEvent(self, event):
        if self.current_tool not in [
            CanvasToolName.ACTIVE_GRID_AREA,
            CanvasToolName.SELECTION
        ]:
            return
        super().mouseMoveEvent(event)
        self.snap_to_grid()

    def mouseReleaseEvent(self, event):
        if self.current_tool in [
            CanvasToolName.ACTIVE_GRID_AREA,
            CanvasToolName.SELECTION
        ]:
            self.snap_to_grid(save=True)
        super().mouseReleaseEvent(event)

    def snap_to_grid(self, save=False):
        x, y = snap_to_grid(
            self.settings,
            int(self.x()),
            int(self.y()),
            False
        )
        x += self.last_pos.x()
        y += self.last_pos.y()
        self.save = save
        self.setPos(x, y)
        self.save = False

    def setPos(self, x, y):
        super().setPos(x, y)
        if self.save:
            if self.current_tool is CanvasToolName.ACTIVE_GRID_AREA:
                settings = self.settings
                active_grid_settings = settings["active_grid_settings"]
                active_grid_settings["pos_x"] = x
                active_grid_settings["pos_y"] = y
                self.settings = settings

    def paint(self, painter: QPainter, option, widget=None):
        painter.drawPixmap(self.pixmap.rect(), self.pixmap)
