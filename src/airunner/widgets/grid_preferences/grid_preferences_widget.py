from PyQt6.QtWidgets import QColorDialog

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

        self.ui.grid_line_width_spinbox.setValue(self.settings_manager.grid_settings.line_width)
        self.ui.grid_size_spinbox.setValue(self.settings_manager.grid_settings.size)
        self.ui.show_grid_checkbox.setChecked(self.settings_manager.grid_settings.show_grid is True)
        self.ui.snap_to_grid_checkbox.setChecked(self.settings_manager.grid_settings.snap_to_grid is True)

        self.ui.grid_line_width_spinbox.blockSignals(False)
        self.ui.grid_size_spinbox.blockSignals(False)
        self.ui.show_grid_checkbox.blockSignals(False)
        self.ui.snap_to_grid_checkbox.blockSignals(False)

    def action_toggled_snap_to_grid(self, val):
        self.settings_manager.set_value("grid_settings.snap_to_grid", val)

    def action_toggled_show_grid(self, val):
        self.settings_manager.set_value("grid_settings.show_grid", val)

    def action_button_clicked_grid_line_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.settings_manager.set_value("grid_settings.line_color", color.name())
            self.app.canvas.update_grid_pen()

    def action_button_clicked_canvas_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.settings_manager.set_value("grid_settings.canvas_color", color.name())
            self.app.canvas.update_canvas_color(color.name())

    def grid_size_changed(self, val):
        self.settings_manager.set_value("grid_settings.size", val)

    def line_width_changed(self, val):
        self.settings_manager.set_value("grid_settings.line_width", val)
