from PyQt6.QtWidgets import QLineEdit

from airunner.widgets.api_token.templates.api_token_ui import Ui_api_token
from airunner.widgets.base_widget import BaseWidget


class APITokenWidget(BaseWidget):
    widget_class_ = Ui_api_token

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui.hf_api_key.blockSignals(True)
        self.ui.hf_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.ui.hf_api_key.setText(self.settings_manager.hf_api_key)
        self.ui.hf_api_key.blockSignals(False)

    def action_text_edited_api_key(self, value):
        self.settings_manager.set_value("hf_api_key", value)
