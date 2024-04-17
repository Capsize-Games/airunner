import os
from PySide6.QtWidgets import QWizard
from airunner.mediator_mixin import MediatorMixin
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.windows.setup_wizard.model_setup.llm_welcome_screen import LLMWelcomeScreen
from airunner.windows.setup_wizard.model_setup.metadata_setup import MetaDataSetup
from airunner.windows.setup_wizard.model_setup.model_setup_page.model_setup_page import ModelSetupPage
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
from airunner.windows.setup_wizard.model_setup.controlnet.controlnet_download import ControlnetDownload
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

        self.page_ids = {}

        self.do_download_sd_models = True
        self.do_download_controlnet_models = True
        self.do_download_llm = True
        self.do_download_tts_models = True
        self.do_download_stt_models = True

        self.pages = {
            "welcome_page": WelcomePage(self),
            "user_agreement": UserAgreement(self),
            "airunner_license": AIRunnerLicense(self),
            "path_settings": PathSettings(self),
            "sd_welcome_screen": StableDiffusionWelcomeScreen(self),
            "model_setup_page": ModelSetupPage(self),
            "stable_diffusion_license": StableDiffusionLicense(self),
            "stable_diffusion_setup_page": StableDiffusionSetupPage(self),
            "controlnet_download": ControlnetDownload(self),
            "final_page": FinalPage(self),
            "llm_welcome_page": LLMWelcomeScreen(self),
            "tts_welcome_page": TTSWelcomeScreen(self),
            "stt_welcome_page": STTWelcomeScreen(self),
            "meta_data_settings": MetaDataSetup(self),
        }

        for page_name, page in self.pages.items():
            self.addPage(page)

        self.welcome_page_id = self.pageIds()[0]
        self.user_agreement_id = self.pageIds()[1]
        self.airunner_license_id = self.pageIds()[2]
        self.path_settings_id = self.pageIds()[3]
        self.sd_welcome_screen_id = self.pageIds()[4]
        self.model_setup_page_id = self.pageIds()[5]
        self.stable_diffusion_license_id = self.pageIds()[6]
        self.stable_diffusion_setup_page_id = self.pageIds()[7]
        self.controlnet_download_id = self.pageIds()[8]
        self.final_page_id = self.pageIds()[9]
        self.llm_welcome_page_id = self.pageIds()[10]
        self.tts_welcome_page_id = self.pageIds()[11]
        self.stt_welcome_page_id = self.pageIds()[12]
        self.meta_data_settings_id = self.pageIds()[13]

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
            self.user_agreement_id,
            self.airunner_license_id,
            self.path_settings_id,
            self.sd_welcome_screen_id,
            self.stable_diffusion_license_id,
            self.controlnet_download_id,
            self.meta_data_settings_id,
            self.llm_welcome_page_id,
            self.tts_welcome_page_id,
            self.stt_welcome_page_id,
            self.final_page_id,
        ]

        if self.do_download_controlnet_models:
            page_order.append(self.controlnet_download_id)  # controlnet_download


        page_order.append(self.meta_data_settings_id)
        page_order.append(self.final_page_id)

        # If the ID of the current page is in the order list, return the ID of the next page
        if current_id in page_order:
            current_index = page_order.index(current_id)

            # If this is not the last page in the list, return the ID of the next page
            if current_index < len(page_order) - 1:

                # final page conditional
                if current_id == self.final_page_id:
                    setup_settings = dict(
                        base_path=self.pages["path_settings"].ui.base_path.text(),
                    )

                    return -1

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
                        return page_order[current_index + 4]
                    else:
                        return page_order[current_index]

                # Controlnet conditional
                elif current_id == self.controlnet_download_id:
                    if self.pages["controlnet_download"].toggled_yes or self.pages["controlnet_download"].toggled_no:
                        return page_order[current_index + 1]
                    else:
                        return page_order[current_index]

                # LLM conditional
                elif current_id == self.llm_welcome_page_id:
                    if self.pages["llm_welcome_page"].toggled_yes or self.pages["llm_welcome_page"].toggled_no:
                        return page_order[current_index + 1]
                    else:
                        return page_order[current_index]

                # TTS conditional
                elif current_id == self.tts_welcome_page_id:
                    if self.pages["tts_welcome_page"].toggled_yes or self.pages["llm_welcome_page"].toggled_no:
                        return page_order[current_index + 1]
                    else:
                        return page_order[current_index]

                # STT conditional
                elif current_id == self.stt_welcome_page_id:
                    if self.pages["stt_welcome_page"].toggled_yes or self.pages["llm_welcome_page"].toggled_no:
                        return page_order[current_index + 1]
                    else:
                        return page_order[current_index]

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
                    if self.validate_path(path):
                        return page_order[current_index + 1]
                    else:
                        return page_order[current_index]
                return page_order[current_index + 1]
            else:
                return -1

        # If the ID of the current page is not in the order list, use the default next page logic
        return super(SetupWizard, self).nextId()

    def validate_path(self, path: str) -> bool:
        """
        Determine if this is a valid path.
        :param path: str
        :return: bool
        """
        valid_path = False
        if os.path.exists(path):
            valid_path = True
        return valid_path
