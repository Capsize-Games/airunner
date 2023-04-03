from PyQt6.QtWidgets import QColorDialog
from airunner.windows.base_window import BaseWindow


class GridSettings(BaseWindow):
    template_name = "grid_settings"
    window_title = "Grid Settings"

    def handle_grid_line_color_button(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.settings_manager.settings.line_color.set(color.name())

    def handle_grid_size_change(self, val):
        self.settings_manager.settings.size.set(val)

    def handle_line_width_change(self, val):
        self.settings_manager.settings.line_width.set(val)

    def handle_show_grid_checkbox(self, val):
        self.settings_manager.settings.show_grid.set(val == 2)

    def handle_snap_to_grid_checkbox(self, val):
        self.settings_manager.settings.snap_to_grid.set(val == 2)

    def initialize_window(self):
        self.template.gridLineColorButton.clicked.connect(self.handle_grid_line_color_button)

        # set the grid_settings_window settings values to the current settings
        self.template.grid_size_spinbox.setValue(self.settings_manager.settings.size.get())

        # on change of grid_size_spinbox, update the settings
        self.template.grid_size_spinbox.valueChanged.connect(self.handle_grid_size_change)

        self.template.grid_line_width_spinbox.setValue(self.settings_manager.settings.line_width.get())
        self.template.grid_line_width_spinbox.valueChanged.connect(self.handle_line_width_change)

        # show_grid_checkbox
        self.template.show_grid_checkbox.setChecked(self.settings_manager.settings.show_grid.get() is True)
        self.template.show_grid_checkbox.stateChanged.connect(self.handle_show_grid_checkbox)

        # snap_to_grid_checkbox
        self.template.snap_to_grid_checkbox.setChecked(self.settings_manager.settings.snap_to_grid.get() is True)
        self.template.snap_to_grid_checkbox.stateChanged.connect(self.handle_snap_to_grid_checkbox)
