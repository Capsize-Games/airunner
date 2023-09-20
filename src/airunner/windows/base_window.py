from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog
from airunner.aihandler.settings_manager import SettingsManager


class BaseWindow(QDialog):
    template_class_ = None
    settings_manager: SettingsManager = None
    template = None
    is_modal: bool = False  # allow the window to be treated as a modal

    def __init__(self, **kwargs):
        super().__init__()
        self.app = kwargs.get("app", None)
        self.do_exec = kwargs.get("exec", True)
        self.settings_manager = SettingsManager(app=self.app)

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
