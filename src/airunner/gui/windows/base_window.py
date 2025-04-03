import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.settings import AIRUNNER_DARK_THEME_NAME, AIRUNNER_LIGHT_THEME_NAME
from airunner.gui.styles.styles_mixin import StylesMixin
from airunner.gui.windows.main.ai_model_mixin import AIModelMixin
from airunner.gui.windows.main.settings_mixin import SettingsMixin


class BaseWindow(
    MediatorMixin,
    SettingsMixin,
    StylesMixin,
    AIModelMixin,
    QDialog,
):
    template_class_ = None
    template = None
    is_modal: bool = False  # allow the window to be treated as a modal
    title: str = "Base Window"

    def __init__(self, **kwargs):
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
