from PySide6.QtCore import Slot
from airunner.gui.windows.setup_wizard.base_wizard import BaseWizard
from airunner.gui.windows.setup_wizard.model_setup.stable_diffusion_setup.templates.stable_diffusion_model_setup_ui import \
    Ui_stable_diffusion_model_setup


class StableDiffusionSetupPage(BaseWizard):
    class_name_ = Ui_stable_diffusion_model_setup

    def __init__(self, *args):
        super(StableDiffusionSetupPage, self).__init__(*args)

        self
