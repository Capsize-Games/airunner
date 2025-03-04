import os
from PySide6.QtWidgets import QFileDialog
from PySide6.QtCore import Slot

from airunner.settings import DEFAULT_PATH_SETTINGS
from airunner.windows.setup_wizard.base_wizard import BaseWizard
from airunner.windows.setup_wizard.path_settings.templates.path_settings_ui import Ui_PathSettings


class PathSettings(BaseWizard):
    class_name_ = Ui_PathSettings

    def __init__(self, *args):
        super(PathSettings, self).__init__(*args)
        self.ui.base_path.setText(self.path_settings.base_path)

    def _update_paths(self, base_path: str):
        self.update_path_settings("base_path", base_path)
        for k, v in DEFAULT_PATH_SETTINGS.items():
            self.update_path_settings(
                k, 
                os.path.expanduser(os.path.join(
                    base_path, 
                    v
                ))
            )

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
        base_path = self.ui.base_path.text()
        self._update_paths(base_path)

    @Slot(str)
    def path_text_changed(self, base_path: str):
        self._update_paths(base_path)
        self.update()