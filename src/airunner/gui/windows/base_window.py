from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog
from airunner.utils.application.mediator_mixin import MediatorMixin
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
    prevent_always_on_top: bool = False

    def __init__(self, prevent_always_on_top: bool = False, **kwargs):
        self.prevent_always_on_top = prevent_always_on_top
        super().__init__()
        self.do_exec = kwargs.get("exec", True)

        self.set_stylesheet()

        self.ui = self.template_class_()
        self.ui.setupUi(self)
        if self.is_modal:
            self.setWindowModality(Qt.WindowModality.WindowModal)
            if not prevent_always_on_top:
                self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle(self.title)
        self.initialize_window()
        if self.do_exec:
            self.exec()

    def initialize_window(self):
        """
        Initialize the window. This method is called after the UI is set up.

        Override this method in subclasses to perform any additional setup.
        """
