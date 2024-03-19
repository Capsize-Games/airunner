from PySide6.QtWidgets import QColorDialog

from airunner.enums import SignalCode
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.brush.templates.brush_widget_ui import Ui_brush_widget


class BrushContainerWidget(BaseWidget):
    widget_class_ = Ui_brush_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui.brush_size_slider.setProperty("current_value", self.settings["brush_settings"]["size"])
        self.ui.brush_size_slider.initialize()
        self.set_button_color()
        self.ui.controlnet.blockSignals(True)
        self.ui.controlnet.clear()
        current_index = 0
        for index, item in enumerate(self.settings["controlnet"]):
            self.ui.controlnet.addItem(item["display_name"])
            if self.settings["generator_settings"]["controlnet_image_settings"]["controlnet"] == item["name"]:
                current_index = index
        self.ui.controlnet.setCurrentIndex(current_index)
        self.ui.controlnet.blockSignals(False)
        self.ui.toggle_auto_generate_while_drawing.blockSignals(True)
        self.ui.toggle_auto_generate_while_drawing.setChecked(self.settings["canvas_settings"]["enable_automatic_drawing"])
        self.ui.toggle_auto_generate_while_drawing.blockSignals(False)

        for k in [
            "brush_size_slider",
            "controlnet_conditioning_scale",
            "controlnet_guidance_scale",
            "strength_slider",
        ]:
            getattr(self.ui, k).settings_loaded(self.callback)

    def callback(self, prop, val):
        settings = self.settings
        if prop in ["strength"]:
            settings["generator_settings"][prop] = val
        elif prop in ["conditioning_scale", "guidance_scale"]:
            settings["generator_settings"]["controlnet_image_settings"][prop] = val
        else:
            settings["brush_settings"][prop] = val
        self.settings = settings

    def toggle_auto_generate_while_drawing(self, val):
        settings = self.settings
        settings["canvas_settings"]["enable_automatic_drawing"] = val
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

    def controlnet_changed(self, val):
        settings = self.settings
        controlnet_value = settings["generator_settings"]["controlnet_image_settings"]["controlnet"]
        for item in self.settings["controlnet"]:
            if item["display_name"] == val:
                controlnet_value = item["name"]
                break
        settings["generator_settings"]["controlnet_image_settings"]["controlnet"] = controlnet_value
        self.settings = settings
