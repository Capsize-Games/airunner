import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog
from airunner.mediator_mixin import MediatorMixin
from airunner.settings import DARK_THEME_NAME, LIGHT_THEME_NAME
from airunner.styles_mixin import StylesMixin
from airunner.windows.main.ai_model_mixin import AIModelMixin
from airunner.windows.main.settings_mixin import SettingsMixin


class BaseWindow(
    QDialog,
    MediatorMixin,
    SettingsMixin,
    StylesMixin,
    AIModelMixin
):
    template_class_ = None
    template = None
    is_modal: bool = False  # allow the window to be treated as a modal
    title: str = "Base Window"

    def __init__(self, **kwargs):
        MediatorMixin.__init__(self)
        
        AIModelMixin.__init__(self)
        super().__init__()
        self.do_exec = kwargs.get("exec", True)

        self.set_stylesheet()

        self.ui = self.template_class_()
        self.ui.setupUi(self)
        if self.is_modal:
            self.setWindowModality(Qt.WindowModality.WindowModal)
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle(self.title)
        self.initialize_window()
        if self.do_exec:
            self.exec()

    def initialize_window(self):
        pass
