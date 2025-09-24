import os

from airunner.components.art.data.controlnet_model import ControlnetModel
from airunner.enums import SignalCode, StableDiffusionVersion
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.art.gui.widgets.controlnet.templates.controlnet_settings_widget_ui import (
    Ui_controlnet_settings_widget,
)


class ControlnetSettingsWidget(BaseWidget):
    widget_class_ = Ui_controlnet_settings_widget

    def __init__(self, *args, **kwargs):
        self._version = None
        self.signal_handlers = {
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL: self.on_application_settings_changed_signal
        }
        super().__init__(*args, **kwargs)

    def showEvent(self, event):
        self._load_controlnet_models()

    def controlnet_changed(self, val):
        self.update_controlnet_settings(controlnet=val)

    def on_application_settings_changed_signal(self):
        self._load_controlnet_models()

    def _load_controlnet_models(self):
        if (
            self._version is None
            or self._version != self.generator_settings.version
        ):
            current_index = 0
            self._version = self.generator_settings.version
            if self._version == StableDiffusionVersion.SDXL_TURBO.value:
                self._version = StableDiffusionVersion.SDXL1_0.value

            controlnet_models = ControlnetModel.objects.filter_by(
                version=self._version
            )
            self.ui.controlnet.blockSignals(True)
            self.ui.controlnet.clear()
            for index, item in enumerate(controlnet_models):
                self.ui.controlnet.addItem(item.display_name)
                if self.controlnet_settings.controlnet == item.display_name:
                    current_index = index
            self.ui.controlnet.setCurrentIndex(current_index)
            self.ui.controlnet.blockSignals(False)
