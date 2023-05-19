import os
from PyQt6 import uic
from PyQt6.QtWidgets import QWidget
from aihandler.settings_manager import SettingsManager


class BaseWindow:
    template_name: str
    window_title: str
    settings_manager: SettingsManager
    template: QWidget

    def __init__(self, settings_manager: SettingsManager, **kwargs):
        self.app = kwargs.get("app", None)
        self.settings_manager = settings_manager
        settings_manager.disable_save()
        self.template = uic.loadUi(os.path.join(f"pyqt/{self.template_name}.ui"))
        self.template.setWindowTitle(self.window_title)
        self.initialize_window()
        settings_manager.enable_save()
        self.template.exec()

    def initialize_window(self):
        pass
