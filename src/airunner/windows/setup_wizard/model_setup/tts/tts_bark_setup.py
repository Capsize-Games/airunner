from airunner.windows.download_wizard.download_thread import DownloadThread
from airunner.windows.download_wizard.download_wizard_page import DownloadWizardPage
from airunner.windows.setup_wizard.model_setup.tts.templates.bark_ui import Ui_bark_setup


class TTSBarkSetup(DownloadWizardPage):
    class_name_ = Ui_bark_setup

    def start_download(self):
        self.models_to_download = [
            {
                "model": {
                    "path": self.bark_settings.processor_path
                },
            },
            {
                "model": {
                    "path": self.bark_settings.voice
                },
            },
            {
                "model": {
                    "path": self.bark_settings.model_path
                },
            }
        ]
        self.download_thread = DownloadThread(self.models_to_download)
        self.download_thread.progress_updated.connect(self.update_progress)
        self.download_thread.download_finished.connect(self.download_finished)
        self.download_thread.start()


