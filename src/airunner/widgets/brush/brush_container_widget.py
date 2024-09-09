from PySide6.QtWidgets import QColorDialog
from airunner.enums import SignalCode
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.brush.templates.brush_widget_ui import Ui_brush_widget


class BrushContainerWidget(BaseWidget):
    widget_class_ = Ui_brush_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        settings = self.settings
        self.ui.brush_size_slider.setProperty("current_value", settings["brush_settings"]["size"])
        self.ui.brush_size_slider.initialize()
        self.set_button_color()
        self.ui.toggle_auto_generate_while_drawing.blockSignals(True)
        self.ui.toggle_auto_generate_while_drawing.setChecked(settings["drawing_pad_settings"]["enable_automatic_drawing"])
        self.ui.toggle_auto_generate_while_drawing.blockSignals(False)

    def toggle_auto_generate_while_drawing(self, val):
        settings = self.settings
        settings["drawing_pad_settings"]["enable_automatic_drawing"] = val
        self.settings = settings

    def color_button_clicked(self):
        color = QColorDialog.getColor()
        if color.isValid():
            settings = self.settings
            settings["brush_settings"]["primary_color"] = color.name()
            self.settings = settings
            self.set_button_color()
            self.emit_signal(
                SignalCode.BRUSH_COLOR_CHANGED_SIGNAL,
                {
                    "color": color.name()
                }
            )

    def set_button_color(self):
        color = self.settings["brush_settings"]["primary_color"]
        self.ui.primary_color_button.setStyleSheet(f"background-color: {color};")
