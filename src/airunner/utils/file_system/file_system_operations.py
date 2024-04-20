import os
from pathlib import Path
from PySide6.QtCore import QObject
from airunner.mediator_mixin import MediatorMixin
from airunner.settings import DARK_THEME_NAME, LIGHT_THEME_NAME
from airunner.windows.main.settings_mixin import SettingsMixin


class FileSystemOperations(
    QObject,
    MediatorMixin,
    SettingsMixin
):
    def __init__(self):
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)
        super().__init__()

        here = Path(os.path.dirname(os.path.realpath(__file__)))
        self.allowed_paths = [
            str(here / ".." / ".." / "styles" / DARK_THEME_NAME / "styles.qss"),
            str(here / ".." / ".." / "styles" / LIGHT_THEME_NAME / "styles.qss"),
        ]

    def _check_path(self, path):
        if path not in self.allowed_paths:
            raise PermissionError(f"Access to {path} is not allowed")

    def read_stylesheet(self):
        theme_name = DARK_THEME_NAME if self.settings["dark_mode_enabled"] else LIGHT_THEME_NAME
        here = Path(os.path.dirname(os.path.realpath(__file__)))
        path = str(here / ".." / ".." / "styles" / theme_name / "styles.qss")

        self._check_path(path)
        stylesheet_path = Path(path)
        return stylesheet_path.read_text()
