from PyQt6.QtWidgets import QFileDialog
from airunner.windows.base_window import BaseWindow


class PreferencesWindow(BaseWindow):
    template_name = "preferences"
    window_title = "Preferences"

    def browse_for_model_base_path(self, line_edit):
        path = QFileDialog.getExistingDirectory(None, "Select Directory")
        line_edit.setText(path)
        self.settings_manager.settings.model_base_path.set(path)

    def initialize_window(self):
        self.template.sd_path.setText(self.settings_manager.settings.model_base_path.get())
        self.template.browseButton.clicked.connect(lambda: self.browse_for_model_base_path(self.template.sd_path))
        self.template.hf_token.setText(self.settings_manager.settings.hf_api_key.get())
        self.template.hf_token.textChanged.connect(lambda val: self.settings_manager.settings.hf_api_key.set(val))
        self.template.sd_path.textChanged.connect(
            lambda val: self.settings_manager.settings.model_base_path.set(val))
