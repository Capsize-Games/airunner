from PySide6.QtCore import QPoint
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QGraphicsItem, QGraphicsPixmapItem

from airunner.enums import CanvasToolName
from airunner.mediator_mixin import MediatorMixin
from airunner.utils.snap_to_grid import snap_to_grid
from airunner.windows.main.settings_mixin import SettingsMixin


class DraggablePixmap(
    QGraphicsPixmapItem,
    MediatorMixin,
    SettingsMixin
):
    def __init__(self, pixmap):
        super().__init__(pixmap)
        MediatorMixin.__init__(self)
        
        self.pixmap = pixmap
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.last_pos = QPoint(0, 0)
        self.save = False
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable,
            True
        )
        x = self.drawing_pad_settings.x_pos
        y = self.drawing_pad_settings.y_pos
        self.setPos(QPoint(x, y))

    @property
    def current_tool(self):
        return CanvasToolName(self.application_settings.current_tool)

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

    def snap_to_grid(self, x=None, y=None, save=False):
        if x is None:
            x = int(self.x())
        if y is None:
            y = int(self.y())
        if self.grid_settings.snap_to_grid:
            x, y = snap_to_grid(self.grid_settings, x, y, False)
        x += self.last_pos.x()
        y += self.last_pos.y()
        self.update_position(x, y, save)

    def update_position(self, x:int, y:int, save:bool=True):
        self.setPos(QPoint(x, y))
        if save:
            self.update_drawing_pad_settings("x_pos", x)
            self.update_drawing_pad_settings("y_pos", y)

    def paint(self, painter: QPainter, option, widget=None):
        painter.drawPixmap(self.pixmap.rect(), self.pixmap)

    def setPixmap(self, pixmap):
        self.pixmap = pixmap
        super().setPixmap(pixmap)
