import os
from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from airunner.aihandler.settings_manager import SettingsManager


class BaseWindow:
    template_name: str = "base_window"
    window_title: str = ""
    settings_manager: SettingsManager = None
    template: QWidget = None
    is_modal: bool = False  # allow the window to be treated as a modal

    def __init__(self, settings_manager: SettingsManager, **kwargs):
        self.app = kwargs.get("app", None)
        self.window_title = kwargs.get("window_title", self.window_title)
        self.exec = kwargs.get("exec", True)
        self.settings_manager = settings_manager
        self.initialize_template()

    def initialize_template(self):
        template_path = os.path.join(f"pyqt/{self.template_name}.ui")
        if os.path.exists(template_path):
            self.template = uic.loadUi(template_path)
        else:
            # create an empty QWiddget with a vertical layout
            self.template = QWidget()
            self.template.setLayout(QVBoxLayout())
        self.template.setWindowTitle(self.window_title)
        if self.is_modal:
            self.template.setWindowModality(Qt.WindowModality.WindowModal)
            self.template.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.initialize_window()
        if self.exec:
            self.show()

    def show(self):
        self.template.exec()

    def initialize_window(self):
        pass
