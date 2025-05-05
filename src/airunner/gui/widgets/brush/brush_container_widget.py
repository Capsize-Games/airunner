from PySide6.QtWidgets import QColorDialog
from airunner.enums import SignalCode
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.brush.templates.brush_widget_ui import (
    Ui_brush_widget,
)


class BrushContainerWidget(BaseWidget):
    widget_class_ = Ui_brush_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui.brush_size_slider.setProperty(
            "current_value", self.brush_settings.size
        )
        self.ui.brush_size_slider.initialize()
        self.set_button_color()
        self.ui.toggle_auto_generate_while_drawing.blockSignals(True)
        self.ui.toggle_auto_generate_while_drawing.setChecked(
            self.drawing_pad_settings.enable_automatic_drawing
        )
        self.ui.toggle_auto_generate_while_drawing.blockSignals(False)

    def toggle_auto_generate_while_drawing(self, val):
        self.drawing_pad_settings.enable_automatic_drawing = val
        self.update_drawing_pad_settings("enable_automatic_drawing", val)

    def color_button_clicked(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.brush_settings.primary_color = color.name()
            self.update_brush_settings("primary_color", color.name())
            self.set_button_color()
            self.api.art.canvas.brush_color_changed(color.name())

    def set_button_color(self):
        color = self.brush_settings.primary_color
        self.ui.primary_color_button.setStyleSheet(
            f"background-color: {color};"
        )
