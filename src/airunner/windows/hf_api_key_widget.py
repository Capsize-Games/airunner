from PyQt6.QtWidgets import QLineEdit

from airunner.windows.custom_widget import CustomWidget


class HFAPIKeyWidget(CustomWidget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs, filename="api_token")

        # handle hf_api_key QLineEdit change
        self.hf_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.hf_api_key.setText(self.settings_manager.hf_api_key)
        self.hf_api_key.textChanged.connect(self.handle_api_key_change)
        # treat self.hf_api_key.textChanged as a password by displaying masked text

    def handle_api_key_change(self, value):
        self.settings_manager.set_value("hf_api_key", value)
