from PySide6.QtWidgets import QWizard
from airunner.mediator_mixin import MediatorMixin
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.windows.setup_wizard.welcome_page import WelcomePage
from airunner.windows.setup_wizard.user_agreement import UserAgreement
from airunner.windows.setup_wizard.stable_diffusion_license import StableDiffusionLicense
from airunner.windows.setup_wizard.ai_runner_license import AIRunnerLicense
from airunner.windows.setup_wizard.path_settings import PathSettings
from airunner.windows.setup_wizard.controlnet_download import ControlnetDownload
from airunner.windows.setup_wizard.tts_speech_t5_setup import TTSSpeechT5Setup
from airunner.windows.setup_wizard.tts_bark_setup import TTSBarkSetup
from airunner.windows.setup_wizard.meta_data_settings import MetaDataSettings
from airunner.windows.setup_wizard.final_page import FinalPage


class SetupWizard(QWizard, MediatorMixin, SettingsMixin):
    def __init__(self):
        super(SetupWizard, self).__init__()

        self.addPage(WelcomePage())

        settings = self.settings
        if not settings["agreements"]["user"]:
            self.addPage(UserAgreement())
        if not settings["agreements"]["stable_diffusion"]:
            self.addPage(StableDiffusionLicense())
        if not settings["agreements"]["airunner"]:
            self.addPage(AIRunnerLicense())

        self.addPage(PathSettings())
        self.addPage(ControlnetDownload())
        self.addPage(TTSSpeechT5Setup())
        self.addPage(TTSBarkSetup())

        # self.addPage(ChooseModelStyle())
        # self.addPage(ChooseModelVersion())
        # self.addPage(ChooseModel())

        self.addPage(MetaDataSettings())
        # self.addPage(ModelDownloadPage())
        self.addPage(FinalPage())
        self.setWindowTitle("AI Runner Setup Wizard")
















