from PySide6.QtCore import Slot
from PySide6.QtWidgets import QWizard
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.gui.windows.main.settings_mixin import SettingsMixin
from airunner.gui.windows.setup_wizard.age_restriction.age_restriction_warning import (
    AgeRestrictionWarning,
)
from airunner.gui.windows.setup_wizard.model_setup.llm.mistral_license import (
    MistralLicense,
)
from airunner.gui.windows.setup_wizard.model_setup.stt.whisper_license import (
    WhisperLicense,
)
from airunner.gui.windows.setup_wizard.model_setup.tts.speecht5_license import (
    SpeechT5License,
)
from airunner.gui.windows.setup_wizard.welcome_page import WelcomePage
from airunner.gui.windows.setup_wizard.user_agreement.user_agreement import (
    UserAgreement,
)
from airunner.gui.windows.setup_wizard.model_setup.stable_diffusion_setup.stable_diffusion_license import (
    StableDiffusionLicense,
)
from airunner.gui.windows.setup_wizard.ai_runner_license.ai_runner_license import (
    AIRunnerLicense,
)


class SetupWizardWindow(
    MediatorMixin,
    SettingsMixin,
    QWizard,
):
    def __init__(self, *args):
        super().__init__(*args)

        self.canceled = False

        # Reset agreements
        self.update_application_settings(
            "stable_diffusion_agreement_checked", False
        )
        self.update_application_settings("airunner_agreement_checked", False)
        self.update_application_settings("user_agreement_checked", False)

        # Set up the wizard pages
        self.final_page_id = None
        self.age_restriction_warning_id = None
        self.welcome_page_id = None
        self.user_agreement_id = None
        self.airunner_license_id = None
        self.controlnet_download_id = None
        self.llm_welcome_page_id = None
        self.tts_welcome_page_id = None
        self.stt_welcome_page_id = None
        self.stable_diffusion_license_id = None
        self.meta_data_settings_id = None
        # self.llama_license_id = None
        self.airunner_license_id = None
        self.setup_settings = dict(
            age_restriction_agreed=False,
            read_age_restriction_agreement=False,
            user_agreement_completed=False,
            airunner_license_completed=False,
            sd_license_completed=False,
            enable_controlnet=False,
            enable_sd=False,
            enable_llm=False,
            enable_tts=False,
            enable_stt=False,
            model_version="",
            model="",
            custom_model="",
            using_custom_model=False,
        )
        self.page_ids = {}
        self.page_order = []
        self.pages = {
            "welcome_page": WelcomePage(self),
            "age_restriction_warning": AgeRestrictionWarning(self),
            "user_agreement": UserAgreement(self),
            "airunner_license": AIRunnerLicense(self),
            "stable_diffusion_license": StableDiffusionLicense(self),
            "mistral_license": MistralLicense(self),
            "whisper_license": WhisperLicense(self),
            "speech_t5_license": SpeechT5License(self),
        }

        for index, key in enumerate(self.pages.keys()):
            page_id = self.addPage(self.pages[key])
            setattr(self, f"{key}_id", page_id)
            self.page_order.append(page_id)

        # Mark the last page as final so QWizard will call accept() when finished
        last_page_key = list(self.pages.keys())[-1]
        self.pages[last_page_key].setFinalPage(True)

        # attach to parent page id changed signal
        self.button(QWizard.WizardButton.CancelButton).clicked.connect(
            self.cancel
        )

        # Set window title
        self.setWindowTitle("AI Runner Setup Wizard")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)

    def addPage(self, page):
        page_id = super().addPage(page)
        self.page_ids[page] = page_id
        return page_id

    def set_page_order(self, page_index):
        self.page_order.append(self.pageIds()[page_index])

    def nextId(self):
        current_id = self.currentId()
        if current_id in self.page_order:
            current_index = self.page_order.index(current_id)
            if current_index < len(self.page_order) - 1:
                return self.page_order[current_index + 1]
            else:
                # Last page: trigger finish
                return -1
        return super(SetupWizardWindow, self).nextId()

    def accept(self):
        print("SetupWizardWindow.accept() called")
        self.canceled = False
        super().accept()

    @Slot()
    def cancel(self):
        print("SetupWizardWindow.cancel() called")
        self.canceled = True
        super().reject()

    def update_application_settings(self, key, value):
        # Only print for non-agreement keys
        if not key.endswith("_agreement_checked"):
            print(f"update_application_settings: {key} = {value}")
        # Fix: Use setattr instead of update for ApplicationSettings
        setattr(self.application_settings, key, value)
        self.application_settings.save()
