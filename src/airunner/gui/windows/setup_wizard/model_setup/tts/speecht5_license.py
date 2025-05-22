from airunner.gui.windows.setup_wizard.model_setup.tts.templates.speecht5_license_ui import (
    Ui_speecht5_license,
)
from airunner.gui.windows.setup_wizard.user_agreement.agreement_page import (
    AgreementPage,
)


class SpeechT5License(AgreementPage):
    class_name_ = Ui_speecht5_license

    def __init__(self, *args):
        super(AgreementPage, self).__init__(*args)
        self.agreed = True
