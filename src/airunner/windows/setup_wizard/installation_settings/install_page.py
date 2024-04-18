from PySide6.QtCore import QObject, QThread, Slot, Signal

from airunner.data.bootstrap.controlnet_bootstrap_data import controlnet_bootstrap_data
from airunner.data.bootstrap.model_bootstrap_data import model_bootstrap_data
from airunner.data.bootstrap.sd_file_bootstrap_data import SD_FILE_BOOTSTRAP_DATA
from airunner.mediator_mixin import MediatorMixin
from airunner.settings import DEFAULT_LLM_HF_PATH, DEFAULT_STT_HF_PATH
from airunner.windows.download_wizard.download_thread import DownloadThread
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.windows.setup_wizard.base_wizard import BaseWizard
from airunner.windows.setup_wizard.installation_settings.templates.install_page_ui import Ui_install_page


class InstallWorker(
    QObject,
    MediatorMixin,
    SettingsMixin
):
    file_download_finished = Signal()
    def __init__(self, parent, setup_settings):
        super(InstallWorker, self).__init__()
        self.parent = parent
        self.setup_settings = setup_settings

    def download_stable_diffusion(self):
        self.parent.set_status("Downloading Stable Diffusion models...")

        model_path = None
        model_name = None
        model_version = None
        using_custom_model = self.setup_settings["using_custom_model"]
        if using_custom_model:
            model_path = self.setup_settings["custom_model"]
        else:
            model_name = self.setup_settings["model"]
            model_version = self.setup_settings["model_version"]

        models_to_download = []
        for model in model_bootstrap_data:
            if using_custom_model:
                models_to_download.append({
                    "model": {
                        "name": "Stable Diffusion 1.5",
                        "path": model_path,
                        "branch": "fp16",
                        "version": "SD 1.5",
                        "category": "stablediffusion",
                        "pipeline_action": "txt2img",
                        "enabled": True,
                        "model_type": "art",
                        "is_default": True
                    }
                })
            else:
                if (
                    model["name"] == model_name and
                    model["version"] == model_version and
                    model["category"] == "stablediffusion" and
                    model["pipeline_action"] != "controlnet"
                ):
                    model["files"] = SD_FILE_BOOTSTRAP_DATA[model_version]
                    self.parent.total_steps += len(model["files"]) + 1
                    self.parent.update_progress_bar()
                    models_to_download.append({
                        "model": model
                    })

        self.download_thread = DownloadThread(models_to_download)
        self.download_thread.file_download_finished.connect(self.file_download_finished)
        self.download_thread.download_finished.connect(self.download_finished)
        self.download_thread.start()

    def download_controlnet(self):
        self.parent.set_status("Downloading Controlnet models...")
        models_to_download = controlnet_bootstrap_data.copy()
        self.download_thread = DownloadThread(models_to_download)
        self.download_thread.progress_updated.connect(self.update_progress)
        self.download_thread.download_finished.connect(self.download_finished)
        self.download_thread.start()

    def download_llms(self):
        if self.setup_settings["enable_llm"]:
            self.parent.set_status("Downloading LLM models...")

            models_to_download = [
                {
                    "model": {
                        "path": DEFAULT_LLM_HF_PATH,
                    },
                }
            ]
            self.download_thread = DownloadThread(models_to_download)
            self.download_thread.progress_updated.connect(self.update_progress)
            self.download_thread.download_finished.connect(self.download_finished)
            self.download_thread.start()

            self.parent.update_progress_bar()

    def download_tts(self):
        if self.setup_settings["enable_tts"]:
            self.parent.set_status("Downloading TTS models...")

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

    def download_stt(self):
        if self.setup_settings["enable_stt"]:
            self.parent.set_status("Downloading STT models...")

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

    def finalize_installation(self):
        self.parent.set_status("Installation complete.")
        self.parent.update_progress_bar()

    def update_progress(self, current, total):
        print("update progress", current, total)

    @Slot()
    def download_finished(self):
        self.parent.update_progress_bar()
        self.set_page()

    def run(self):
        if (
            self.setup_settings["user_agreement_completed"] and
            self.setup_settings["airunner_license_completed"]
        ):
            self.current_step = None
            self.set_page()

    def set_page(self):
        has_model = (
            self.setup_settings["model_version"] and
            self.setup_settings["model"]
        ) or (
            self.setup_settings["using_custom_model"] and
            self.setup_settings["custom_model"]
        )
        model_path = self.setup_settings["model"] if not self.setup_settings["using_custom_model"] \
            else self.setup_settings["custom_model"]

        if (
            self.setup_settings["enable_sd"] and
            self.setup_settings["sd_license_completed"] and
            has_model and
            self.current_step is None
        ):
            self.parent.set_status(f"Downloading {model_path}...")
            self.current_step = 0
            self.download_stable_diffusion()
        elif self.setup_settings["enable_llm"] and self.current_step < 1:
            self.current_step = 1
            self.download_llms()
        elif self.setup_settings["enable_tts"] and self.current_step < 2:
            self.current_step = 2
            self.download_tts()
        elif self.setup_settings["enable_stt"] and self.current_step < 3:
            self.current_step = 3
            self.download_stt()
        else:
            self.current_step = 4
            self.finalize_installation()


class InstallPage(BaseWizard):
    class_name_ = Ui_install_page

    def __init__(self, parent, setup_settings):
        super(InstallPage, self).__init__(parent)
        self.setup_settings = setup_settings

        # reset the progress bar
        self.ui.progress_bar.setValue(0)
        self.ui.progress_bar.setMaximum(100)

        self.total_steps = 6
        if not self.setup_settings["enable_sd"] or not self.setup_settings["sd_license_completed"]:
            self.total_steps -= 1
        if not self.setup_settings["enable_controlnet"]:
            self.total_steps -= 1
        if not self.setup_settings["enable_llm"]:
            self.total_steps -= 1
        if not self.setup_settings["enable_tts"]:
            self.total_steps -= 1
        if not self.setup_settings["enable_stt"]:
            self.total_steps -= 1

        self.thread = QThread()
        self.worker = InstallWorker(self, setup_settings)
        self.worker.file_download_finished.connect(self.update_progress_bar)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    def update_progress_bar(self):
        self.total_steps -= 1
        if self.total_steps == 0:
            self.ui.progress_bar.setValue(100)
        else:
            self.ui.progress_bar.setValue(100 / self.total_steps)

    def set_status(self, status):
        self.ui.status.setText(status)
