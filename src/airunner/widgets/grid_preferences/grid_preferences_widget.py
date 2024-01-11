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

        line_width = self.app.application_settings.value('line_width', 1, type=int)
        cell_size = self.app.application_settings.value('cell_size', 64, type=int)
        show_grid = self.app.application_settings.value('show_grid', False, type=bool)
        snap_to_grid = self.app.application_settings.value('snap_to_grid', False, type=bool)

        self.ui.grid_line_width_spinbox.setValue(line_width)
        self.ui.grid_size_spinbox.setValue(cell_size)
        self.ui.show_grid_checkbox.setChecked(show_grid is True)
        self.ui.snap_to_grid_checkbox.setChecked(snap_to_grid is True)

        self.ui.grid_line_width_spinbox.blockSignals(False)
        self.ui.grid_size_spinbox.blockSignals(False)
        self.ui.show_grid_checkbox.blockSignals(False)
        self.ui.snap_to_grid_checkbox.blockSignals(False)

    def action_toggled_snap_to_grid(self, val):
         self.app.snap_to_grid_changed(val)

    def action_toggled_show_grid(self, val):
        self.app.action_toggle_grid(val)

    def action_button_clicked_grid_line_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.app.line_color_changed(color.name())

    def action_button_clicked_canvas_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.app.canvas_color_changed(color.name())

    def grid_size_changed(self, val):
        self.app.grid_size_changed(val)

    def line_width_changed(self, val):
        self.app.line_width_changed(val)
