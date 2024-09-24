from PySide6.QtWidgets import QFileDialog
from PySide6.QtCore import Slot

from airunner.settings import BASE_PATH
from airunner.utils.os.create_airunner_directory import create_airunner_paths
from airunner.windows.setup_wizard.base_wizard import BaseWizard
from airunner.windows.setup_wizard.path_settings.templates.path_settings_ui import Ui_PathSettings


class PathSettings(BaseWizard):
    class_name_ = Ui_PathSettings

    def __init__(self, *args):
        super(PathSettings, self).__init__(*args)

        self.ui.base_path.setText(BASE_PATH)

    @Slot()
    def browse_files(self):
        base_path = str(self.path_settings.base_path)
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.Directory)
        file_dialog.setOption(QFileDialog.ShowDirsOnly)
        file_dialog.setDirectory(base_path)
        file_dialog.setModal(True)
        file_dialog.exec_()
        selected_path = file_dialog.selectedFiles()
        if selected_path:
            self.ui.base_path.setText(selected_path[0])

    def save_settings(self):
        self.update_path_settings("base_path", self.ui.base_path.text())

        """
        Create the airunner paths
        """
        create_airunner_paths(self.path_settings)
        self.update_application_settings("paths_initialized", True)
