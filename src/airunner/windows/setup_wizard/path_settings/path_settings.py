from airunner.utils.create_airunner_directory import create_airunner_paths
from airunner.windows.setup_wizard.base_wizard import BaseWizard
from airunner.windows.setup_wizard.metadata_settings.templates.metadata_settings_ui import Ui_PathSettings


class PathSettings(BaseWizard):
    class_name_ = Ui_PathSettings

    def initialize_form(self):
        self.ui.base_path.setText(self.settings["path_settings"]["base_path"])

    def save_settings(self):
        print("CREATING AI RUNNER PATHS")
        settings = self.settings
        settings["path_settings"]["base_path"] = self.ui.base_path.text()
        create_airunner_paths(self.settings["path_settings"])
        settings["paths_initialized"] = True
        self.settings = settings
