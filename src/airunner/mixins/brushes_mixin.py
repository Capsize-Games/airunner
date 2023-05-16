from PyQt6.QtWidgets import QColorDialog


class BrushesMixin:
    def initialize(self):
        self.window.primary_color_button.clicked.connect(self.set_primary_color)
        self.window.secondary_color_button.clicked.connect(self.set_secondary_color)
        self.window.primary_brush_opacity_slider.valueChanged.connect(self.set_primary_brush_opacity)
        self.window.secondary_brush_opacity_slider.valueChanged.connect(self.set_secondary_brush_opacity)
        self.window.primary_brush_opacity_slider.setValue(self.settings_manager.settings.primary_brush_opacity.get())
        self.window.secondary_brush_opacity_slider.setValue(self.settings_manager.settings.secondary_brush_opacity.get())
        self.set_button_colors()

    def reset_settings(self):
        self.window.primary_brush_opacity_slider.setValue(self.settings_manager.settings.primary_brush_opacity.get())
        self.window.secondary_brush_opacity_slider.setValue(self.settings_manager.settings.secondary_brush_opacity.get())
        self.window.primary_color_button.setStyleSheet(f"background-color: {self.settings_manager.settings.primary_color.get()};")
        self.window.secondary_color_button.setStyleSheet(f"background-color: {self.settings_manager.settings.secondary_color.get()};")
        self.window.brush_size_slider.setValue(self.settings_manager.settings.size.get())

    def set_primary_brush_opacity(self, value):
        self.settings_manager.settings.primary_brush_opacity.set(int(value))
        self.canvas.update()

    def set_secondary_brush_opacity(self, value):
        self.settings_manager.settings.secondary_brush_opacity.set(int(value))
        self.canvas.update()

    def set_primary_color(self):
        # display a color picker
        color = QColorDialog.getColor()
        if color.isValid():
            self.settings_manager.settings.primary_color.set(color.name())
            self.set_button_colors()

    def set_secondary_color(self):
        # display a color picker
        color = QColorDialog.getColor()
        if color.isValid():
            self.settings_manager.settings.secondary_color.set(color.name())
            self.set_button_colors()

    def set_button_colors(self):
        self.window.primary_color_button.setStyleSheet(
            f"background-color: {self.settings_manager.settings.primary_color.get()};"
        )
        self.window.secondary_color_button.setStyleSheet(
            f"background-color: {self.settings_manager.settings.secondary_color.get()};"
        )
