from airunner.gui.windows.setup_wizard.user_agreement.agreement_page import AgreementPage
from airunner.gui.windows.setup_wizard.ai_runner_license.templates.airunner_license_ui import Ui_airunner_license


class AIRunnerLicense(AgreementPage):
    class_name_ = Ui_airunner_license
    setting_key = "airunner_agreement_checked"
