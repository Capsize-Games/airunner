from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QGraphicsView

from airunner.enums import CanvasToolName
from airunner.mediator_mixin import MediatorMixin
from airunner.windows.main.settings_mixin import SettingsMixin


class CustomGraphicsView(
    QGraphicsView,
    MediatorMixin,
    SettingsMixin
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)

    def adjust_to_grid(self, event: QMouseEvent) -> QMouseEvent:
        """
        This is used to adjust the selection tool to the grid
        in real time.
        :param event:
        :return:
        """
        if (
            self.settings["grid_settings"]["snap_to_grid"] and
            self.settings["current_tool"] == CanvasToolName.SELECTION
        ):
            cell_size = self.settings["grid_settings"]["cell_size"]
            grid_x = round(event.pos().x() / cell_size) * cell_size
            grid_y = round(event.pos().y() / cell_size) * cell_size
        else:
            grid_x = event.pos().x()
            grid_y = event.pos().y()

        # Create a new event with the adjusted position
        new_event = QMouseEvent(
            event.type(),
            QPointF(grid_x, grid_y),
            event.button(),
            event.buttons(),
            event.modifiers()
        )
        return new_event

    def mousePressEvent(self, event: QMouseEvent):
        new_event = self.adjust_to_grid(event)
        super().mousePressEvent(new_event)

    def mouseMoveEvent(self, event: QMouseEvent):
        new_event = self.adjust_to_grid(event)
        super().mouseMoveEvent(new_event)
