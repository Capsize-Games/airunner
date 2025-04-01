
from PySide6.QtWidgets import QLineEdit

from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.civitai_preferences.templates.civitai_preferences_widget_ui import Ui_civitai_preferences


class CivitAIPreferencesWidget(BaseWidget):
    widget_class_ = Ui_civitai_preferences

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui.api_key.blockSignals(True)
        self.ui.api_key.setEchoMode(QLineEdit.EchoMode.Password)  # Set echo mode to Password
        self.ui.api_key.setText(self.application_settings.civit_ai_api_key)
        self.ui.api_key.blockSignals(False)

    def on_text_changed(self, text):
        self.update_application_settings('civitai_api_key', text)
