from PyQt6.QtWidgets import QFileDialog
from airunner.windows.base_window import BaseWindow


class PreferencesWindow(BaseWindow):
    template_name = "preferences"
    window_title = "Preferences"

    def initialize_window(self):
        self.template.browseButton.clicked.connect(
            lambda: self.browse_for_model_base_path(self.template.sd_path))
        self.template.sd_path.textChanged.connect(
            lambda val: self.settings_manager.settings.model_base_path.set(val))
        self.template.embeddings_path.textChanged.connect(
            lambda val: self.settings_manager.settings.embeddings_path.set(val))
        self.template.embeddings_browse_button.clicked.connect(
            lambda: self.browse_for_embeddings_path(self.template.embeddings_path))
        self.template.sd_path.setText(self.settings_manager.settings.model_base_path.get())
        self.template.embeddings_path.setText(self.settings_manager.settings.embeddings_path.get())
        # self.template.hf_token.textChanged.connect(
        #     lambda val: self.settings_manager.settings.hf_api_key.set(val))
        # self.template.hf_token.setText(self.settings_manager.settings.hf_api_key.get())
        self.template.extensions_path.textChanged.connect(
            lambda val: self.settings_manager.settings.extensions_path.set(val))
        self.template.extensions_path.setText(
            self.settings_manager.settings.extensions_path.get())
        self.template.extensions_browse_button.clicked.connect(
            lambda: self.browse_for_extensions_path(self.template.extensions_path))
        self.app.do_preferences_injection(self)

    def browse_for_extensions_path(self, line_edit):
        path = QFileDialog.getExistingDirectory(None, "Select Directory")
        line_edit.setText(path)
        self.settings_manager.settings.extensions_path.set(path)

    def browse_for_embeddings_path(self, line_edit):
        path = QFileDialog.getExistingDirectory(None, "Select Directory")
        line_edit.setText(path)
        self.settings_manager.settings.embeddings_path.set(path)

    def browse_for_lora_path(self, line_edit):
        path = QFileDialog.getExistingDirectory(None, "Select Directory")
        line_edit.setText(path)
        self.settings_manager.settings.lora_path.set(path)

    def browse_for_model_base_path(self, line_edit):
        path = QFileDialog.getExistingDirectory(None, "Select Directory")
        line_edit.setText(path)
        self.settings_manager.settings.model_base_path.set(path)
