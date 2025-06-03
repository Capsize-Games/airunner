from PySide6.QtCore import Slot
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.openrouter_settings.templates.openrouter_settings_ui import (
    Ui_openrouter_settings_widget,
)


class OpenrouterSettingsWidget(BaseWidget):
    widget_class_ = Ui_openrouter_settings_widget

    def showEvent(self, event):
        super().showEvent(event)
        self.ui.api_key.setEchoMode(self.ui.api_key.EchoMode.Password)
        self.ui.api_key.setPlaceholderText("OpenRouter API Key")
        self.ui.api_key.setText(self.settings.value("openrouter/api_key", ""))
        self.ui.allow.blockSignals(True)
        self.ui.allow.setChecked(
            self.settings.value("openrouter/allow_downloads", "false")
            == "true"
        )
        self.ui.allow.blockSignals(False)

    @Slot(bool)
    def on_allow_toggled(self, val: bool):
        self.settings.setValue("openrouter/allow_downloads", val)

    @Slot(str)
    def on_api_key_textChanged(self, val: str):
        self.settings.setValue("openrouter/api_key", val)
