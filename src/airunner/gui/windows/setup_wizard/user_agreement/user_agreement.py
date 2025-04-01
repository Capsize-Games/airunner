from airunner.gui.windows.setup_wizard.user_agreement.agreement_page import AgreementPage
from airunner.gui.windows.setup_wizard.user_agreement.templates.user_agreement_ui import Ui_user_agreement


class UserAgreement(AgreementPage):
    class_name_ = Ui_user_agreement
    setting_key = "user_agreement_checked"

