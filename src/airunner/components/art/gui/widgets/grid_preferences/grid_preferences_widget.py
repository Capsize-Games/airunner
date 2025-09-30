from typing import Dict
from PySide6.QtWidgets import QColorDialog
from PySide6.QtCore import Slot

from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.art.gui.widgets.grid_preferences.templates.grid_preferences_ui import (
    Ui_grid_preferences,
)
from airunner.enums import SignalCode


class GridPreferencesWidget(BaseWidget):
    widget_class_ = Ui_grid_preferences

    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.TOGGLE_GRID: self.on_toggle_grid_signal,
            SignalCode.TOGGLE_GRID_SNAP: self.on_toggle_grid_snap_signal,
        }
        super().__init__(*args, **kwargs)
        self.ui.grid_line_width_spinbox.blockSignals(True)
        self.ui.grid_size_spinbox.blockSignals(True)
        self.ui.show_grid_checkbox.blockSignals(True)
        self.ui.snap_to_grid_checkbox.blockSignals(True)

        self.ui.grid_line_width_spinbox.setValue(self.grid_settings.line_width)
        self.ui.grid_size_spinbox.setValue(self.grid_settings.cell_size)
        self.ui.show_grid_checkbox.setChecked(self.grid_settings.show_grid)
        self.ui.snap_to_grid_checkbox.setChecked(
            self.grid_settings.snap_to_grid
        )

        self.ui.grid_line_width_spinbox.blockSignals(False)
        self.ui.grid_size_spinbox.blockSignals(False)
        self.ui.show_grid_checkbox.blockSignals(False)
        self.ui.snap_to_grid_checkbox.blockSignals(False)

    @Slot(bool)
    def on_snap_to_grid_checkbox_toggled(self, val: bool):
        self.api.art.canvas.toggle_grid_snap(val)

    @Slot(bool)
    def on_show_grid_checkbox_toggled(self, val: bool):
        self.api.art.canvas.toggle_grid(val)

    @Slot()
    def on_grid_line_color_button_clicked(self):
        color = QColorDialog.getColor(parent=self)
        if color.isValid():
            self.grid_settings.line_color = color.name()
            self.update_grid_settings(line_color=color.name())

    @Slot()
    def on_canvas_color_button_clicked(self):
        color = QColorDialog.getColor(parent=self)
        if color.isValid():
            self.grid_settings.canvas_color = color.name()
            self.update_grid_settings(canvas_color=color.name())

    def grid_size_changed(self, val):
        self.grid_settings.cell_size = val
        self.update_grid_settings(cell_size=val)

    def line_width_changed(self, val):
        self.grid_settings.line_width = val
        self.update_grid_settings(line_width=val)

    def on_toggle_grid_signal(self, data: Dict):
        show_grid = data.get("show_grid", False)
        self.ui.show_grid_checkbox.blockSignals(True)
        self.ui.show_grid_checkbox.setChecked(show_grid)
        self.ui.show_grid_checkbox.blockSignals(False)

    def on_toggle_grid_snap_signal(self, data: Dict):
        snap_to_grid = data.get("snap_to_grid", False)
        self.ui.snap_to_grid_checkbox.blockSignals(True)
        self.ui.snap_to_grid_checkbox.setChecked(snap_to_grid)
        self.ui.snap_to_grid_checkbox.blockSignals(False)
