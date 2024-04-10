from airunner.windows.setup_wizard.agreement_page import AgreementPage
from airunner.windows.setup_wizard.templates.stable_diffusion_license_ui import Ui_stable_diffusion_license


class StableDiffusionLicense(AgreementPage):
    class_name_ = Ui_stable_diffusion_license
    setting_key = "stable_diffusion"


