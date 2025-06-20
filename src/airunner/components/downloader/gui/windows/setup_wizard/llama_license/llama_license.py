from airunner.components.downloader.gui.windows.setup_wizard.llama_license.templates.llama_license_ui import (
    Ui_llama_license,
)
from airunner.components.downloader.gui.windows.setup_wizard.user_agreement.agreement_page import (
    AgreementPage,
)


class LlamaLicense(AgreementPage):
    class_name_ = Ui_llama_license
    setting_key = "llama_license"

    def __init__(self, *args):
        super(AgreementPage, self).__init__(*args)
        self.agreed = True
