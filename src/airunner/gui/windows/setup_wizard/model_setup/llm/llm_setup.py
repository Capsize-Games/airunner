from airunner.settings import AIRUNNER_DEFAULT_LLM_HF_PATH
from airunner.gui.windows.download_wizard.download_thread import DownloadThread
from airunner.gui.windows.download_wizard.download_wizard_page import DownloadWizardPage
from airunner.gui.windows.setup_wizard.model_setup.llm.templates.llm_setup_ui import Ui_llm_setup


class LLMSetup(DownloadWizardPage):
    class_name_ = Ui_llm_setup

    def start_download(self):
        self.models_to_download = [
            {
                "model": {
                    "path": AIRUNNER_DEFAULT_LLM_HF_PATH
                },
            }
        ]
        self.download_thread = DownloadThread(self.models_to_download)
        self.download_thread.progress_updated.connect(self.update_progress)
        self.download_thread.download_finished.connect(self.download_finished)
        self.download_thread.start()
