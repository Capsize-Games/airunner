from PyQt6.QtWidgets import QColorDialog

from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.brush.templates.brush_widget_ui import Ui_brush_widget


class BrushContainerWidget(BaseWidget):
    widget_class_ = Ui_brush_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui.brush_size_slider.setProperty("current_value", self.settings["brush_settings"]["size"])
        self.ui.brush_size_slider.initialize()
        self.set_button_color()

    def color_button_clicked(self):
        color = QColorDialog.getColor()
        if color.isValid():
            settings = self.settings
            settings["brush_settings"]["primary_color"] = color.name()
            self.settings = settings
            self.set_button_color()

    def set_button_color(self):
        color = self.settings["brush_settings"]["primary_color"]
        self.ui.primary_color_button.setStyleSheet(f"background-color: {color};")