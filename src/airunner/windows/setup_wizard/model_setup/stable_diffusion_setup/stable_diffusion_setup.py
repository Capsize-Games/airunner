from PySide6.QtCore import Slot
from airunner.windows.setup_wizard.base_wizard import BaseWizard
from airunner.windows.setup_wizard.model_setup.stable_diffusion_setup.templates.stable_diffusion_model_setup_ui import \
    Ui_stable_diffusion_model_setup


class StableDiffusionSetupPage(BaseWizard):
    class_name_ = Ui_stable_diffusion_model_setup

    def __init__(self, *args):
        super(StableDiffusionSetupPage, self).__init__(*args)
        self.no_toggled = False
        self.yes_toggled = False

    @Slot(bool)
    def no_toggled(self, val: bool):
        self.no_toggled = val

    @Slot(bool)
    def yes_toggled(self, val: bool):
        self.yes_toggled = val
