from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QColorDialog


class BrushesMixin:
    def set_primary_color(self):
        # display a color picker and keep on top
        color_name: str = self.settings_manager.brush_settings.primary_color
        qcolor = QColor(color_name)
        color_dialog = QColorDialog(self)
        # color = self.layout().addWidget(color_dialog)
        color = color_dialog.getColor(qcolor, None, "Select Color")
        if color.isValid():
            self.settings_manager.set_value("brush_settings.primary_color", color.name())
