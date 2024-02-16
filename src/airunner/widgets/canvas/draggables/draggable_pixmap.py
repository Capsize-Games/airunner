from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsPixmapItem

from airunner.enums import CanvasToolName
from airunner.mediator_mixin import MediatorMixin
from airunner.service_locator import ServiceLocator
from airunner.utils import snap_to_grid


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

    def snap_to_grid(self):
        x, y = snap_to_grid(
            int(self.x()),
            int(self.y())
        )
        x += self.last_pos.x()
        y += self.last_pos.y()
        self.setPos(x, y)

    def paint(self, painter: QPainter, option, widget=None):
        painter.drawPixmap(self.pixmap.rect(), self.pixmap)
