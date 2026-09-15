from airunner.components.downloader.gui.windows.setup_wizard.model_setup.stt.templates.whisper_license_ui import (
    Ui_whisper_license,
)
from airunner.components.downloader.gui.windows.setup_wizard.user_agreement.agreement_page import (
    AgreementPage,
)


class WhisperLicense(AgreementPage):
    class_name_ = Ui_whisper_license

    def __init__(self, *args):
        super(AgreementPage, self).__init__(*args)
        self.agreed = True
