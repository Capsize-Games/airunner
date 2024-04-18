from PySide6.QtCore import Slot
from airunner.windows.setup_wizard.base_wizard import BaseWizard
from airunner.windows.setup_wizard.model_setup.llm.templates.llm_welcome_screen_ui import Ui_llm_welcome_screen


class LLMWelcomeScreen(BaseWizard):
    class_name_ = Ui_llm_welcome_screen

    def __init__(self, *args):
        super(LLMWelcomeScreen, self).__init__(*args)
        self.toggled_no = False
        self.toggled_yes = True

    @Slot(bool)
    def no_toggled(self, val: bool):
        self.toggled_no = val
        self.toggled_yes = not val

    @Slot(bool)
    def yes_toggled(self, val: bool):
        self.toggled_yes = val
        self.toggled_no = not val
