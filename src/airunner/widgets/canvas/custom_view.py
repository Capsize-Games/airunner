from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QGraphicsView

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
        cell_size = self.settings["grid_settings"]["cell_size"]
        # Calculate the grid cell coordinates
        grid_x = round(event.pos().x() / cell_size) * cell_size
        grid_y = round(event.pos().y() / cell_size) * cell_size

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
        # Pass the new event to the base class's method
        super().mousePressEvent(new_event)

    def mouseMoveEvent(self, event: QMouseEvent):
        new_event = self.adjust_to_grid(event)
        # Pass the new event to the base class's method
        super().mouseMoveEvent(new_event)
