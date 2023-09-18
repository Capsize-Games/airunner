from PyQt6.QtWidgets import QColorDialog
from airunner.windows.custom_widget import CustomWidget


class GridWidget(CustomWidget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs, filename="grid_preferences")

        self.gridLineColorButton.clicked.connect(self.handle_grid_line_color_button)
        self.canvas_color.clicked.connect(self.handle_canvas_color_button)

        self.grid_size_spinbox.setValue(self.settings_manager.grid_settings.size)
        self.grid_size_spinbox.valueChanged.connect(self.handle_grid_size_change)

        self.grid_line_width_spinbox.setValue(self.settings_manager.grid_settings.line_width)
        self.grid_line_width_spinbox.valueChanged.connect(self.handle_line_width_change)

        self.show_grid_checkbox.setChecked(self.settings_manager.grid_settings.show_grid is True)
        self.show_grid_checkbox.stateChanged.connect(self.handle_show_grid_checkbox)

        self.snap_to_grid_checkbox.setChecked(self.settings_manager.grid_settings.snap_to_grid is True)
        self.snap_to_grid_checkbox.stateChanged.connect(self.handle_snap_to_grid_checkbox)

    def handle_grid_line_color_button(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.settings_manager.set_value("grid_settings.line_color", color.name())
            self.app.canvas.update_grid_pen()

    def handle_canvas_color_button(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.settings_manager.set_value("grid_settings.canvas_color", color.name())
            self.app.canvas.update_canvas_color(color.name())

    def handle_grid_size_change(self, val):
        self.settings_manager.set_value("grid_settings.size", val)
        self.app.canvas.update()

    def handle_line_width_change(self, val):
        self.settings_manager.set_value("grid_settings.line_width", val)
        self.app.canvas.update()

    def handle_show_grid_checkbox(self, val):
        self.settings_manager.set_value("grid_settings.show_grid", val == 2)
        self.app.canvas.update()

    def handle_snap_to_grid_checkbox(self, val):
        self.settings_manager.set_value("grid_settings.snap_to_grid", val == 2)
        self.app.canvas.update()
