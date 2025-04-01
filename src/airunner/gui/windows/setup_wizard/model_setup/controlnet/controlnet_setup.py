from PySide6.QtCore import Slot
from airunner.gui.windows.setup_wizard.base_wizard import BaseWizard
from airunner.gui.windows.setup_wizard.model_setup.controlnet.templates.controlnet_setup_ui import Ui_controlnet_setup


class ControlnetSetup(BaseWizard):
    class_name_ = Ui_controlnet_setup

    def __init__(self, *args):
        super(ControlnetSetup, self).__init__(*args)
        self.toggled_no = False
        self.toggled_yes = True

    @Slot(bool)
    def no_toggled(self, val: bool):
        self.toggled_no = val

    @Slot(bool)
    def yes_toggled(self, val: bool):
        self.toggled_yes = val
