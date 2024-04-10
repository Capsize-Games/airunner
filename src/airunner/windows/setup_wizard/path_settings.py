from airunner.windows.setup_wizard.base_wizard import BaseWizard
from airunner.windows.setup_wizard.templates.metadata_settings_ui import Ui_PathSettings


class PathSettings(BaseWizard):
    class_name_ = Ui_PathSettings

    def initialize_form(self):
        self.ui.base_path.setText(self.settings["path_settings"]["base_path"])

    def save_settings(self):
        settings = self.settings
        settings["path_settings"]["base_path"] = self.ui.base_path.text()
        self.settings = settings

