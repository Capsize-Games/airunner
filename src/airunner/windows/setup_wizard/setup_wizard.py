from PySide6.QtWidgets import QWizard
from airunner.mediator_mixin import MediatorMixin
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.windows.setup_wizard.model_setup.llm.llm_setup import LLMSetup
from airunner.windows.setup_wizard.model_setup.model_setup_page.model_setup_page import ModelSetupPage
from airunner.windows.setup_wizard.model_setup.stable_diffusion_setup.stable_diffusion_setup import \
    StableDiffusionSetupPage
from airunner.windows.setup_wizard.model_setup.stt.stt_setup import STTSetup
from airunner.windows.setup_wizard.welcome_page import WelcomePage
from airunner.windows.setup_wizard.user_agreement.user_agreement import UserAgreement
from airunner.windows.setup_wizard.model_setup.stable_diffusion_setup.stable_diffusion_license import \
    StableDiffusionLicense
from airunner.windows.setup_wizard.ai_runner_license.ai_runner_license import AIRunnerLicense
from airunner.windows.setup_wizard.path_settings.path_settings import PathSettings
from airunner.windows.setup_wizard.model_setup.controlnet.controlnet_download import ControlnetDownload
from airunner.windows.setup_wizard.model_setup.tts.tts_speech_t5_setup import TTSSpeechT5Setup
from airunner.windows.setup_wizard.model_setup.tts.tts_bark_setup import TTSBarkSetup
from airunner.windows.setup_wizard.metadata_settings.meta_data_settings import MetaDataSettings
from airunner.windows.setup_wizard.final_page import FinalPage


class SetupWizard(
    QWizard,
    MediatorMixin,
    SettingsMixin
):
    def __init__(self, *args):
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)
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
            "stable_diffusion_license": StableDiffusionLicense(self),
            "airunner_license": AIRunnerLicense(self),
            "path_settings": PathSettings(self),
            "model_setup_page": ModelSetupPage(self),
            "stable_diffusion_setup_page": StableDiffusionSetupPage(self),
            "controlnet_download": ControlnetDownload(self),
            "llm_setup": LLMSetup(self),
            "tts_speech_t5_setup": TTSSpeechT5Setup(self),
            "tts_bark_setup": TTSBarkSetup(self),
            "stt_setup": STTSetup(self),
            "meta_data_settings": MetaDataSettings(self),
            "final_page": FinalPage(self)
        }

        for page_name, page in self.pages.items():
            self.addPage(page)

        self.setWindowTitle("AI Runner Setup Wizard")

    def addPage(self, page):
        page_id = super().addPage(page)
        self.page_ids[page] = page_id
        return page_id

    def nextId(self):
        # Get the ID of the current page
        current_id = self.currentId()

        # Define the order of the pages based on the boolean values
        page_order = [
            self.pageIds()[0],  # welcome_page is always first
            self.pageIds()[1],  # user_agreement
            self.pageIds()[2],  # stable_diffusion_license
            self.pageIds()[3],  # airunner_license
            self.pageIds()[4],  # path_settings
            self.pageIds()[5]  # model_setup_page
        ]

        if self.do_download_sd_models:
            page_order.append(self.pageIds()[6])  # stable_diffusion_setup_page
        if self.do_download_controlnet_models:
            page_order.append(self.pageIds()[7])  # controlnet_download
        if self.do_download_llm:
            page_order.append(self.pageIds()[8])  # llm_setup
        if self.do_download_tts_models:
            page_order.append(self.pageIds()[9])  # tts_speech_t5_setup
            page_order.append(self.pageIds()[10])  # tts_bark_setup
        if self.do_download_stt_models:
            page_order.append(self.pageIds()[11])  # stt_setup
        page_order.append(self.pageIds()[12])  # meta_data_settings is always last before final_page
        page_order.append(self.pageIds()[13])  # final_page is always last

        # If the ID of the current page is in the order list, return the ID of the next page
        if current_id in page_order:
            current_index = page_order.index(current_id)
            # If this is not the last page in the list, return the ID of the next page
            if current_index < len(page_order) - 1:
                if current_id == 0:  # welcome_page
                    if not self.settings["agreements"]["user"]:
                        return page_order[current_index + 1]
                    elif not self.settings["agreements"]["stable_diffusion"]:
                        return page_order[current_index + 2]
                    elif not self.settings["agreements"]["airunner"]:
                        return page_order[current_index + 3]
                    else:
                        return page_order[current_index + 4]
                if current_id == 1:  # user_agreement
                    if self.settings["agreements"]["user"]:
                        return page_order[current_index + 1]
                    else:
                        return page_order[current_index]
                elif current_id == 2:  # stable_diffusion_license
                    if self.settings["agreements"]["stable_diffusion"]:
                        return page_order[current_index + 1]
                    else:
                        return page_order[current_index]
                elif current_id == 3:  # airunner_license
                    if self.settings["agreements"]["airunner"]:
                        return page_order[current_index + 1]
                    else:
                        return page_order[current_index]
                return page_order[current_index + 1]
            # If this is the last page in the list, return -1 to indicate the end of the wizard
            else:
                return -1

        # If the ID of the current page is not in the order list, use the default next page logic
        return super(SetupWizard, self).nextId()
