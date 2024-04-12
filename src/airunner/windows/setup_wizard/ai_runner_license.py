from airunner.windows.setup_wizard.agreement_page import AgreementPage
from airunner.windows.setup_wizard.templates.airunner_license_ui import Ui_airunner_license


class AIRunnerLicense(AgreementPage):
    class_name_ = Ui_airunner_license
    setting_key = "airunner"

