import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog
from airunner.mediator_mixin import MediatorMixin
from airunner.service_locator import ServiceLocator
from airunner.windows.main.settings_mixin import SettingsMixin


class BaseWindow(QDialog, MediatorMixin, SettingsMixin):
    template_class_ = None
    template = None
    is_modal: bool = False  # allow the window to be treated as a modal

    def __init__(self, **kwargs):
        SettingsMixin.__init__(self)
        super().__init__()
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
        theme_name = "dark_theme" if self.settings["dark_mode_enabled"] else "light_theme"
        here = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(here, "..", "styles", theme_name, "styles.qss"), "r") as f:
            stylesheet = f.read()
        self.setStyleSheet(stylesheet)