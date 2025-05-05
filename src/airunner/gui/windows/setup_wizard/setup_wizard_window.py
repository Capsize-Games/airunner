from PySide6.QtCore import Slot
from PySide6.QtWidgets import QWizard
from airunner.api import API
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
        # Get the ID of the current page
        current_id = self.currentId()

        # If the ID of the current page is in the order list, return the ID of the next page
        if current_id in self.page_order:
            current_index = self.page_order.index(current_id)

            # If this is not the last page in the list, return the ID of the next page
            if current_index < len(self.page_order) - 1:

                # final page conditional
                if current_id == self.final_page_id:
                    age_restriction_warning = self.pages[
                        "age_restriction_warning"
                    ].read_age_restriction_agreement
                    self.setup_settings = dict(
                        age_restriction_agreed=self.pages[
                            "age_restriction_warning"
                        ].age_restriction_agreed,
                        read_age_restriction_agreement=age_restriction_warning,
                        user_agreement_completed=self.pages[
                            "user_agreement"
                        ].agreed,
                        airunner_license_completed=self.pages[
                            "airunner_license"
                        ].agreed,
                        sd_license_completed=self.pages[
                            "stable_diffusion_license"
                        ].agreed,
                    )

                    return -1

                elif current_id == self.age_restriction_warning_id:
                    if (
                        self.pages[
                            "age_restriction_warning"
                        ].age_restriction_agreed
                        and self.pages[
                            "age_restriction_warning"
                        ].read_age_restriction_agreement
                    ):
                        return self.page_order[current_index + 1]
                    else:
                        return self.page_order[current_index]

                elif current_id == self.welcome_page_id:
                    return self.page_order[current_index + 1]

                # User agreement conditional
                elif current_id == self.user_agreement_id:
                    if self.pages["user_agreement"].agreed:
                        return self.page_order[current_index + 1]
                    else:
                        return self.page_order[current_index]

                # AI Runner license conditional
                elif current_id == self.airunner_license_id:
                    if self.pages["airunner_license"].agreed:
                        return self.page_order[current_index + 1]
                    else:
                        return self.page_order[current_index]

                # Stable Diffusion license conditional
                elif current_id == self.stable_diffusion_license_id:
                    if self.pages["stable_diffusion_license"].agreed:
                        return self.page_order[current_index + 1]
                    else:
                        return self.page_order[current_index]

                # # AI Runner license conditional
                # elif current_id == self.airunner_license_id:
                #     if self.application_settings.airunner_agreement_checked:
                #         return self.page_order[current_index + 1]
                #     else:
                #         return self.page_order[current_index]

                return self.page_order[current_index + 1]
            else:
                return -1

        # If the ID of the current page is not in the order list, use the default next page logic
        return super(SetupWizardWindow, self).nextId()

    @Slot()
    def cancel(self):
        self.canceled = True
