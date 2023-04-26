import os
from PyQt6 import uic


class BaseWindow:
    template_name = ""
    window_title = ""
    settings_manager = None
    template = None
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        settings_manager.disable_save()
        self.template = uic.loadUi(os.path.join(f"pyqt/{self.template_name}.ui"))
        self.template.setWindowTitle(self.window_title)
        self.initialize_window()
        settings_manager.enable_save()
        self.template.exec()

    def initialize_window(self):
        pass
