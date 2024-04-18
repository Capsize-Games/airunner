from PySide6.QtWidgets import QWizard
from airunner.mediator_mixin import MediatorMixin
from airunner.utils.os_utils.validate_path import validate_path
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.windows.setup_wizard.age_restriction.age_restriction_warning import AgeRestrictionWarning
from airunner.windows.setup_wizard.model_setup.controlnet.controlnet_setup import ControlnetSetup
from airunner.windows.setup_wizard.model_setup.llm_welcome_screen import LLMWelcomeScreen
from airunner.windows.setup_wizard.model_setup.metadata_setup import MetaDataSetup
from airunner.windows.setup_wizard.model_setup.stable_diffusion_setup.choose_model import ChooseModel
from airunner.windows.setup_wizard.model_setup.stable_diffusion_setup.stable_diffusion_setup import (
    StableDiffusionSetupPage
)
from airunner.windows.setup_wizard.model_setup.stable_diffusion_setup.stable_diffusion_welcome_screen import \
    StableDiffusionWelcomeScreen
from airunner.windows.setup_wizard.model_setup.stt_welcome_screen import STTWelcomeScreen
from airunner.windows.setup_wizard.model_setup.tts_welcome_screen import TTSWelcomeScreen
from airunner.windows.setup_wizard.welcome_page import WelcomePage
from airunner.windows.setup_wizard.user_agreement.user_agreement import UserAgreement
from airunner.windows.setup_wizard.model_setup.stable_diffusion_setup.stable_diffusion_license import (
    StableDiffusionLicense
)
from airunner.windows.setup_wizard.ai_runner_license.ai_runner_license import AIRunnerLicense
from airunner.windows.setup_wizard.path_settings.path_settings import PathSettings
from airunner.windows.setup_wizard.final_page import FinalPage


class SetupWizard(
    QWizard,
    MediatorMixin,
    SettingsMixin
):
    def __init__(self, *args):
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)
        self.reset_paths()
        super(SetupWizard, self).__init__(*args)

        # Reset agreements
        settings = self.settings
        settings["agreements"]["user"] = False
        settings["agreements"]["stable_diffusion"] = False
        settings["agreements"]["airunner"] = False
        self.settings = settings

        self.setup_settings = dict(
            age_restriction_agreed=False,
            read_age_restriction_agreement=False,
            user_agreement_completed=False,
            airunner_license_completed=False,
            sd_license_completed=False,
            base_path=False,
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

        self.pages = {
            "welcome_page": WelcomePage(self),
            "age_restriction_warning": AgeRestrictionWarning(self),
            "user_agreement": UserAgreement(self),
            "airunner_license": AIRunnerLicense(self),
            "path_settings": PathSettings(self),
            "sd_welcome_screen": StableDiffusionWelcomeScreen(self),
            "stable_diffusion_license": StableDiffusionLicense(self),
            "stable_diffusion_setup_page": StableDiffusionSetupPage(self),
            "choose_model_page": ChooseModel(self),
            "controlnet_download": ControlnetSetup(self),
            "final_page": FinalPage(self),
            "llm_welcome_page": LLMWelcomeScreen(self),
            "tts_welcome_page": TTSWelcomeScreen(self),
            "stt_welcome_page": STTWelcomeScreen(self),
            "meta_data_settings": MetaDataSetup(self),
        }

        for page_name, page in self.pages.items():
            self.addPage(page)

        self.welcome_page_id = self.pageIds()[0]
        self.age_restriction_agreement_id = self.pageIds()[1]
        self.user_agreement_id = self.pageIds()[2]
        self.airunner_license_id = self.pageIds()[3]
        self.path_settings_id = self.pageIds()[4]
        self.sd_welcome_screen_id = self.pageIds()[5]
        self.stable_diffusion_license_id = self.pageIds()[6]
        self.stable_diffusion_setup_page_id = self.pageIds()[7]
        self.choose_model_page_id = self.pageIds()[8]
        self.controlnet_download_id = self.pageIds()[9]
        self.final_page_id = self.pageIds()[10]
        self.llm_welcome_page_id = self.pageIds()[11]
        self.tts_welcome_page_id = self.pageIds()[12]
        self.stt_welcome_page_id = self.pageIds()[13]
        self.meta_data_settings_id = self.pageIds()[14]

    def addPage(self, page):
        page_id = super().addPage(page)
        self.page_ids[page] = page_id
        return page_id

    def set_page_order(self, page_index):
        self.page_order.append(self.pageIds()[page_index])

    def nextId(self):
        # Get the ID of the current page
        current_id = self.currentId()

        # Define the order of the pages based on the boolean values
        page_order = [
            self.welcome_page_id,
            self.age_restriction_agreement_id,
            self.user_agreement_id,
            self.airunner_license_id,
            self.path_settings_id,
            self.sd_welcome_screen_id,
            self.stable_diffusion_license_id,
            self.choose_model_page_id,
            self.controlnet_download_id,
            self.meta_data_settings_id,
            self.llm_welcome_page_id,
            self.tts_welcome_page_id,
            self.stt_welcome_page_id,
            self.final_page_id,
        ]

        page_order.append(self.meta_data_settings_id)
        page_order.append(self.final_page_id)

        # If the ID of the current page is in the order list, return the ID of the next page
        if current_id in page_order:
            current_index = page_order.index(current_id)

            # If this is not the last page in the list, return the ID of the next page
            if current_index < len(page_order) - 1:

                # final page conditional
                if current_id == self.final_page_id:
                    self.setup_settings = dict(
                        age_restriction_agreed=self.pages["age_restriction_warning"].age_restriction_agreed,
                        read_age_restriction_agreement=self.pages["age_restriction_warning"].read_age_restriction_agreement,
                        user_agreement_completed=self.pages["user_agreement"].agreed,
                        airunner_license_completed=self.pages["airunner_license"].agreed,
                        sd_license_completed=self.pages["stable_diffusion_license"].agreed,
                        base_path=self.pages["path_settings"].ui.base_path.text(),
                        enable_sd=self.pages["sd_welcome_screen"].toggled_yes,
                        enable_controlnet=self.pages["controlnet_download"].toggled_yes,
                        enable_llm=self.pages["llm_welcome_page"].toggled_yes,
                        enable_tts=self.pages["tts_welcome_page"].toggled_yes,
                        enable_stt=self.pages["stt_welcome_page"].toggled_yes,
                        model_version=self.pages["choose_model_page"].model_version,
                        model=self.pages["choose_model_page"].model,
                        custom_model=self.pages["choose_model_page"].custom_model,
                        using_custom_model=self.pages["choose_model_page"].using_custom_model,
                    )

                    return -1

                elif current_id == self.age_restriction_agreement_id:
                    if self.pages["age_restriction_warning"].age_restriction_agreed and \
                            self.pages["age_restriction_warning"].read_age_restriction_agreement:
                        return page_order[current_index + 1]
                    else:
                        return page_order[current_index]

                elif current_id == self.welcome_page_id:
                    if not self.settings["agreements"]["user"]:
                        return page_order[current_index + 1]
                    elif not self.settings["agreements"]["stable_diffusion"]:
                        return page_order[current_index + 2]
                    elif not self.settings["agreements"]["airunner"]:
                        return page_order[current_index + 3]
                    else:
                        return page_order[current_index + 4]

                # User agreement conditional
                elif current_id == self.user_agreement_id:
                    if self.settings["agreements"]["user"]:
                        return page_order[current_index + 1]
                    else:
                        return page_order[current_index]

                # AI Runner license conditional
                elif current_id == self.airunner_license_id:
                    if self.settings["agreements"]["airunner"]:
                        return page_order[current_index + 1]
                    else:
                        return page_order[current_index]

                # Stable diffusion conditional
                elif current_id == self.sd_welcome_screen_id:
                    if self.pages["sd_welcome_screen"].toggled_yes:
                        return page_order[current_index + 1]
                    elif self.pages["sd_welcome_screen"].toggled_no:
                        return page_order[current_index + 3]
                    else:
                        return page_order[current_index]

                # Model setup page conditional
                # elif current_id == self.choose_model_page_id:
                #     if self.pages["choose_model_page"].toggled_yes:
                #         return page_order[current_index + 1]
                #     elif self.pages["choose_model_page"].toggled_no:
                #         return page_order[current_index + 2]
                #     else:
                #         return page_order[current_index]

                # Controlnet conditional
                elif current_id == self.controlnet_download_id:
                    if self.pages["controlnet_download"].toggled_yes is False \
                            and self.pages["controlnet_download"].toggled_no is False:
                        return page_order[current_index]
                    else:
                        return page_order[current_index + 1]

                # LLM conditional
                elif current_id == self.llm_welcome_page_id:
                    if self.pages["llm_welcome_page"].toggled_yes is False \
                            and self.pages["llm_welcome_page"].toggled_no is False:
                        return page_order[current_index]
                    else:
                        return page_order[current_index + 1]

                # TTS conditional
                elif current_id == self.tts_welcome_page_id:
                    if self.pages["tts_welcome_page"].toggled_yes is False \
                            and self.pages["tts_welcome_page"].toggled_no is False:
                        return page_order[current_index]
                    else:
                        return page_order[current_index + 1]

                # STT conditional
                elif current_id == self.stt_welcome_page_id:
                    if self.pages["stt_welcome_page"].toggled_yes is False \
                            and self.pages["stt_welcome_page"].toggled_no is False:
                        return page_order[current_index]
                    else:
                        return page_order[current_index + 1]

                # Metadata conditional
                elif current_id == self.meta_data_settings_id:
                    if self.pages["meta_data_settings"].toggled_yes is False \
                            and self.pages["meta_data_settings"].toggled_no is False:
                        return page_order[current_index]
                    else:
                        return page_order[current_index + 1]

                # Stable Diffusion license conditional
                elif current_id == self.stable_diffusion_license_id:
                    if self.settings["agreements"]["stable_diffusion"]:
                        return page_order[current_index + 1]
                    else:
                        return page_order[current_index]

                # AI Runner license conditional
                elif current_id == self.airunner_license_id:
                    if self.settings["agreements"]["airunner"]:
                        return page_order[current_index + 1]
                    else:
                        return page_order[current_index]

                # Path settings
                elif self.path_settings_id:
                    """
                    Prevent Path settings from progressing unless the path has been set
                    in the UI.
                    """
                    path: str = self.pages["path_settings"].ui.base_path.text()
                    is_valid_path = validate_path(path)
                    print(path, is_valid_path)
                    if is_valid_path:
                        return page_order[current_index + 1]
                    else:
                        return page_order[current_index]
                return page_order[current_index + 1]
            else:
                return -1

        # If the ID of the current page is not in the order list, use the default next page logic
        return super(SetupWizard, self).nextId()
