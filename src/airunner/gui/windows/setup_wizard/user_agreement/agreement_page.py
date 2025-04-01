from PySide6.QtCore import Slot
from airunner.gui.windows.setup_wizard.base_wizard import BaseWizard


class AgreementPage(BaseWizard):
    setting_key = ""

    def __init__(self, *args):
        super(AgreementPage, self).__init__(*args)
        self.agreed = False

    @Slot(bool)
    def agreement_clicked(self, val):
        self.agreed = val
        self.update_application_settings(self.setting_key, val)

