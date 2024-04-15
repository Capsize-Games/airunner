from airunner.windows.setup_wizard.download_wizard.download_thread import DownloadThread
from airunner.windows.setup_wizard.download_wizard.download_wizard import DownloadWizard
from airunner.windows.setup_wizard.model_setup.tts.templates.speech_t5_ui import Ui_speecht5_setup


class TTSSpeechT5Setup(DownloadWizard):
    class_name_ = Ui_speecht5_setup

    def start_download(self):
        self.models_to_download = [
            {
                "model": {
                    "path": self.settings["tts_settings"]["speecht5"]["embeddings_path"],
                    "repo_type": "dataset",
                },
            },
            {
                "model": {
                    "path": self.settings["tts_settings"]["speecht5"]["vocoder_path"]
                },
            },
            {
                "model": {
                    "path": self.settings["tts_settings"]["speecht5"]["model_path"]
                },
            }
        ]
        self.download_thread = DownloadThread(self.models_to_download)
        self.download_thread.progress_updated.connect(self.update_progress)
        self.download_thread.download_finished.connect(self.download_finished)
        self.download_thread.start()

