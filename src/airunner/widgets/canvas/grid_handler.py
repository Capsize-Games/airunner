from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt

from airunner.mediator_mixin import MediatorMixin
from airunner.windows.main.settings_mixin import SettingsMixin


class GridHandler(
    SettingsMixin,
    MediatorMixin
):
    MAX_WORKING_HEIGHT: int = 4096
    MIN_WORKING_HEIGHT: int = 512
    MAX_WORKING_WIDTH: int = 4096
    MIN_WORKING_WIDTH: int = 512
    WHEEL_DELTA_DIVISOR: int = 120
    OPERATION_INCREASE: str = "increase"
    OPERATION_DECREASE: str = "decrease"
    DIMENSION_WIDTH: str = "width"
    DIMENSION_HEIGHT: str = "height"

    def __init__(self):
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)

    def update_grid_dimensions_based_on_event(self, event):
        amount = int(abs(event.angleDelta().y()) / self.WHEEL_DELTA_DIVISOR)
        operation = self.OPERATION_INCREASE if event.angleDelta().y() > 0 else self.OPERATION_DECREASE
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers == Qt.KeyboardModifier.ControlModifier:
            self.update_grid_dimension(self.DIMENSION_HEIGHT, operation, amount)
        elif modifiers == Qt.KeyboardModifier.ShiftModifier:
            self.update_grid_dimension(self.DIMENSION_WIDTH, operation, amount)
        elif modifiers == Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier:
            self.update_grid_dimension(self.DIMENSION_HEIGHT, operation, amount)
            self.update_grid_dimension(self.DIMENSION_WIDTH, operation, amount)

    def update_grid_dimension(self, dimension, operation, amount):
        if dimension == self.DIMENSION_HEIGHT:
            if operation == self.OPERATION_INCREASE:
                self.increase_active_grid_height(amount)
            else:
                self.decrease_active_grid_height(amount)
        elif dimension == self.DIMENSION_WIDTH:
            if operation == self.OPERATION_INCREASE:
                self.increase_active_grid_width(amount)
            else:
                self.decrease_active_grid_width(amount)

    def increase_active_grid_height(self, amount):
        self.update_setting("working_height", self.OPERATION_INCREASE, amount, self.MAX_WORKING_HEIGHT)

    def decrease_active_grid_height(self, amount):
        self.update_setting("working_height", self.OPERATION_DECREASE, amount, self.MIN_WORKING_HEIGHT)

    def increase_active_grid_width(self, amount):
        self.update_setting("is_maximized", self.OPERATION_INCREASE, amount, self.MAX_WORKING_WIDTH)

    def decrease_active_grid_width(self, amount):
        self.update_setting("is_maximized", self.OPERATION_DECREASE, amount, self.MIN_WORKING_WIDTH)

    def update_setting(self, key: str, operation: str, amount: int, limit: int):
        value = self.settings[key]
        if operation == self.OPERATION_INCREASE:
            value += self.settings["grid_settings"]["cell_size"] * amount
            if value > limit:
                value = limit
        elif operation == self.OPERATION_DECREASE:
            value -= self.settings["grid_settings"]["cell_size"] * amount
            if value < limit:
                value = limit
        self.settings[key] = value
