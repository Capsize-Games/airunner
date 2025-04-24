from PySide6.QtCore import Slot
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.huggingface_settings.templates.huggingface_settings_ui import (
    Ui_huggingface_settings_widget,
)


class HuggingfaceSettingsWidget(BaseWidget):
    widget_class_ = Ui_huggingface_settings_widget

    def showEvent(self, event):
        super().showEvent(event)
        self.ui.api_key.setEchoMode(self.ui.api_key.EchoMode.Password)
        self.ui.api_key.setPlaceholderText("Huggingface API Key")
        self.ui.api_key.setText(self.settings.value("huggingface/api_key", ""))
        self.ui.allow.blockSignals(True)
        self.ui.allow.setChecked(
            self.settings.value("huggingface/allow_downloads", "false")
            == "true"
        )
        self.ui.allow.blockSignals(False)

    @Slot(bool)
    def on_allow_toggled(self, val: bool):
        self.settings.setValue("huggingface/allow_downloads", val)

    @Slot(str)
    def on_api_key_textChanged(self, val: str):
        self.settings.setValue("huggingface/api_key", val)
