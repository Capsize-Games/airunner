from PySide6.QtCore import Slot

from airunner.windows.setup_wizard.base_wizard import BaseWizard
from airunner.windows.setup_wizard.model_setup.model_setup_page.templates.model_setup_ui import Ui_model_setup_page


class ModelSetupPage(BaseWizard):
    class_name_ = Ui_model_setup_page

    @Slot(bool)
    def toggle_download_sd_models(self, val):
        self.wizard().do_download_sd_models = val

    @Slot(bool)
    def toggle_download_controlnet_models(self, val):
        self.wizard().do_download_controlnet_models = val

    @Slot(bool)
    def toggle_download_llms(self, val):
        self.wizard().do_download_llm = val

    @Slot(bool)
    def toggle_download_tts_models(self, val):
        self.wizard().do_download_tts_models = val

    @Slot(bool)
    def toggle_download_stt_models(self, val):
        self.wizard().do_download_stt_models = val
