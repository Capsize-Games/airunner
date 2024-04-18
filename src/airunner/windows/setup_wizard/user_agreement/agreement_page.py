from PySide6.QtCore import Slot
from airunner.windows.setup_wizard.base_wizard import BaseWizard


class AgreementPage(BaseWizard):
    setting_key = ""

    def __init__(self, *args):
        super(AgreementPage, self).__init__(*args)
        self.agreed = False

    @Slot(bool)
    def agreement_clicked(self, val):
        self.agreed = val
        settings = self.settings
        settings["agreements"][self.setting_key] = val
        self.settings = settings

