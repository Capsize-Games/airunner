from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QGraphicsView

from airunner.enums import CanvasToolName
from airunner.mediator_mixin import MediatorMixin
from airunner.utils import snap_to_grid
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

    def snap_to_grid(self, event: QMouseEvent, use_floor: bool = True) -> QMouseEvent:
        """
        This is used to adjust the selection tool to the grid
        in real time during rubberband mode.
        :param event:
        :return:
        """
        if self.settings["current_tool"] == CanvasToolName.SELECTION:
            x, y = snap_to_grid(event.pos().x(), event.pos().y(), use_floor)
        else:
            x = event.pos().x()
            y = event.pos().y()

        # Create a new event with the adjusted position
        new_event = QMouseEvent(
            event.type(),
            QPointF(x, y),
            event.button(),
            event.buttons(),
            event.modifiers()
        )
        return new_event

    def mousePressEvent(self, event: QMouseEvent):
        new_event = self.snap_to_grid(event)
        super().mousePressEvent(new_event)

    def mouseMoveEvent(self, event: QMouseEvent):
        new_event = self.snap_to_grid(event, False)
        super().mouseMoveEvent(new_event)
