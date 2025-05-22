from PySide6.QtCore import Slot
from airunner.gui.windows.setup_wizard.user_agreement.agreement_page import (
    AgreementPage,
)
from airunner.gui.windows.setup_wizard.user_agreement.templates.user_agreement_ui import (
    Ui_user_agreement,
)


class UserAgreement(AgreementPage):
    class_name_ = Ui_user_agreement
    setting_key = "user_agreement_checked"

    @Slot(bool)
    def agreement_clicked(self, val):
        super().agreement_clicked(val)
        self.update_application_settings(self.setting_key, val)
