from PySide6.QtCore import Slot
from airunner.gui.windows.setup_wizard.base_wizard import BaseWizard
from airunner.gui.windows.setup_wizard.model_setup.tts.templates.tts_welcome_screen_ui import Ui_tts_welcome_screen


class TTSWelcomeScreen(BaseWizard):
    class_name_ = Ui_tts_welcome_screen

    def __init__(self, *args):
        super(TTSWelcomeScreen, self).__init__(*args)
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
