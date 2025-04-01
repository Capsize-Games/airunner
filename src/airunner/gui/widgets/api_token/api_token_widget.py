
from PySide6.QtWidgets import QLineEdit
from airunner.gui.widgets.api_token.templates.api_token_ui import Ui_api_token
from airunner.gui.widgets.base_widget import BaseWidget


class APITokenWidget(BaseWidget):
    widget_class_ = Ui_api_token

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui.hf_api_key_text_generation.blockSignals(True)
        self.ui.hf_api_key_text_generation.setEchoMode(QLineEdit.EchoMode.Password)
        self.ui.hf_api_key_text_generation.setText(self.application_settings.hf_api_key_read_key)

        self.ui.hf_api_key_writetoken.blockSignals(True)
        self.ui.hf_api_key_writetoken.setEchoMode(QLineEdit.EchoMode.Password)
        self.ui.hf_api_key_writetoken.setText(self.application_settings.hf_api_key_read_key)

        self.ui.hf_api_key_text_generation.blockSignals(False)
        self.ui.hf_api_key_writetoken.blockSignals(False)

    def action_text_edited_api_key(self, value):
        self.update_application_settings("hf_api_key_read_key", value)

    def action_text_edited_writekey(self, value):
        self.update_settings("hf_api_key_read_key", value)
