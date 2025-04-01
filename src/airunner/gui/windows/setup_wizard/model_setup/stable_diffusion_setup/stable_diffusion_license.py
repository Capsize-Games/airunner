from airunner.gui.windows.setup_wizard.user_agreement.agreement_page import AgreementPage
from airunner.gui.windows.setup_wizard.model_setup.stable_diffusion_setup.templates.stable_diffusion_license_ui import Ui_stable_diffusion_license


class StableDiffusionLicense(AgreementPage):
    class_name_ = Ui_stable_diffusion_license
    setting_key = "stable_diffusion_agreement_checked"
