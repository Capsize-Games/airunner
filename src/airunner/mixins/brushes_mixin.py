from PyQt6.QtWidgets import QColorDialog


class BrushesMixin:
    def initialize(self):
        self.window.primary_color_button.clicked.connect(self.set_primary_color)
        self.set_button_colors()

    def reset_settings(self):
        self.window.primary_color_button.setStyleSheet(f"background-color: {self.settings_manager.settings.primary_color.get()};")
        self.window.brush_size_slider.setValue(self.settings_manager.settings.size.get())

    def set_primary_color(self):
        # display a color picker
        color = QColorDialog.getColor()
        if color.isValid():
            self.settings_manager.settings.primary_color.set(color.name())
            self.set_button_colors()

    def set_button_colors(self):
        self.window.primary_color_button.setStyleSheet(
            f"background-color: {self.settings_manager.settings.primary_color.get()};"
        )
