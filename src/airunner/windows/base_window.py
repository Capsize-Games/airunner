import os
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog
from airunner.data.managers import SettingsManager
from airunner.utils import get_main_window


class BaseWindow(QDialog):
    template_class_ = None
    settings_manager: SettingsManager = None
    template = None
    is_modal: bool = False  # allow the window to be treated as a modal

    def __init__(self, **kwargs):
        super().__init__()
        self.app = get_main_window()
        self.do_exec = kwargs.get("exec", True)

        self.set_stylesheet()

        self.ui = self.template_class_()
        self.ui.setupUi(self)
        if self.is_modal:
            self.setWindowModality(Qt.WindowModality.WindowModal)
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.initialize_window()
        if self.do_exec:
            self.exec()

    def initialize_window(self):
        pass

    def set_stylesheet(self):
        """
        Sets the stylesheet for the application based on the current theme
        """
        theme_name = "dark_theme" if self.app.settings_manager.settings.dark_mode_enabled else "light_theme"
        here = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(here, "..", "styles", theme_name, "styles.qss"), "r") as f:
            stylesheet = f.read()
        self.setStyleSheet(stylesheet)
