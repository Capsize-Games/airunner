from airunner.components.downloader.gui.windows.setup_wizard.model_setup.llm.templates.mistral_license_ui import (
    Ui_mistral_license,
)
from airunner.components.downloader.gui.windows.setup_wizard.user_agreement.agreement_page import (
    AgreementPage,
)


class MistralLicense(AgreementPage):
    class_name_ = Ui_mistral_license

    def __init__(self, *args):
        super(AgreementPage, self).__init__(*args)
        self.agreed = True
