from PySide6.QtWidgets import QColorDialog

from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.grid_preferences.templates.grid_preferences_ui import Ui_grid_preferences


class GridPreferencesWidget(BaseWidget):
    widget_class_ = Ui_grid_preferences

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui.grid_line_width_spinbox.blockSignals(True)
        self.ui.grid_size_spinbox.blockSignals(True)
        self.ui.show_grid_checkbox.blockSignals(True)
        self.ui.snap_to_grid_checkbox.blockSignals(True)

        line_width = self.settings["grid_settings"]["line_width"]
        cell_size = self.settings["grid_settings"]["cell_size"]
        show_grid = self.settings["grid_settings"]["show_grid"]
        snap_to_grid = self.settings["grid_settings"]["snap_to_grid"]

        self.ui.grid_line_width_spinbox.setValue(line_width)
        self.ui.grid_size_spinbox.setValue(cell_size)
        self.ui.show_grid_checkbox.setChecked(show_grid is True)
        self.ui.snap_to_grid_checkbox.setChecked(snap_to_grid is True)

        self.ui.grid_line_width_spinbox.blockSignals(False)
        self.ui.grid_size_spinbox.blockSignals(False)
        self.ui.show_grid_checkbox.blockSignals(False)
        self.ui.snap_to_grid_checkbox.blockSignals(False)

    def action_toggled_snap_to_grid(self, val):
        settings = self.settings
        settings["grid_settings"]["snap_to_grid"] = val
        self.settings = settings

    def action_toggled_show_grid(self, val):
        settings = self.settings
        settings["grid_settings"]["show_grid"] = val
        self.settings = settings

    def action_button_clicked_grid_line_color(self):
        color = QColorDialog.getColor(parent=self)
        if color.isValid():
            settings = self.settings
            settings["grid_settings"]["line_color"] = color.name()
            self.settings = settings

    def action_button_clicked_canvas_color(self):
        color = QColorDialog.getColor(parent=self)
        if color.isValid():
            settings = self.settings
            settings["grid_settings"]["canvas_color"] = color.name()
            self.settings = settings

    def grid_size_changed(self, val):
        settings = self.settings
        settings["grid_settings"]["cell_size"] = val
        self.settings = settings

    def line_width_changed(self, val):
        settings = self.settings
        settings["grid_settings"]["line_width"] = val
        self.settings = settings
