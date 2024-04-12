from PySide6.QtCore import Slot

from airunner.windows.setup_wizard.base_wizard import BaseWizard


class AgreementPage(BaseWizard):
    setting_key = ""

    def __init__(self):
        super(AgreementPage, self).__init__()
        self.user_agreement_clicked = False

    @Slot(bool)
    def agreement_clicked(self, val):
        self.user_agreement_clicked = val
        settings = self.settings
        settings["agreements"][self.setting_key] = val
        self.settings = settings

    def nextId(self):
        if self.user_agreement_clicked:
            return super().nextId()

