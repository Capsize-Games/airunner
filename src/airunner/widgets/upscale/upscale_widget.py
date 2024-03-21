from airunner.enums import SignalCode
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.upscale.templates.upscale_widget_ui import Ui_upscale_widget


class UpscaleWidget(BaseWidget):
    widget_class_ = Ui_upscale_widget

    def model_changed(self, val):
        settings = self.settings
        settings["upscale_settings"]["model"] = val
        self.settings = settings

    def face_enhance_toggled(self, val):
        settings = self.settings
        settings["upscale_settings"]["face_enhance"] = val
        self.settings = settings

    def upscale_amount_changed(self, val):
        settings = self.settings
        settings["upscale_settings"]["upscale_amount"] = val
        self.settings = settings

    def upscale_clicked(self):
        self.emit_signal(SignalCode.UPSCALE_SIGNAL, self.settings["upscale_settings"])
