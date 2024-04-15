from airunner.windows.setup_wizard.download_wizard.download_thread import DownloadThread
from airunner.windows.setup_wizard.download_wizard.download_wizard import DownloadWizard
from airunner.windows.setup_wizard.model_setup.stt.templates.stt_setup_ui import Ui_stt_setup


class STTSetup(DownloadWizard):
    class_name_ = Ui_stt_setup

    def start_download(self):
        self.models_to_download = [
            {
                "model": {
                    "path": DEFAULT_STT_HF_PATH
                },
            }
        ]
        self.download_thread = DownloadThread(self.models_to_download)
        self.download_thread.progress_updated.connect(self.update_progress)
        self.download_thread.download_finished.connect(self.download_finished)
        self.download_thread.start()
