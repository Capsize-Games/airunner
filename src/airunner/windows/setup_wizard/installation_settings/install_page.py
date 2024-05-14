import os.path

import nltk
from PySide6.QtCore import QObject, QThread, Slot, Signal
from airunner.data.bootstrap.model_bootstrap_data import model_bootstrap_data
from airunner.data.bootstrap.sd_file_bootstrap_data import SD_FILE_BOOTSTRAP_DATA
from airunner.data.bootstrap.llm_file_bootstrap_data import LLM_FILE_BOOTSTRAP_DATA
from airunner.data.bootstrap.whisper import WHISPER_FILES
from airunner.data.bootstrap.speech_t5 import SPEECH_T5_FILES
from airunner.enums import SignalCode
from airunner.mediator_mixin import MediatorMixin
from airunner.settings import DEFAULT_LLM_HF_PATH, NLTK_DOWNLOAD_DIR
from airunner.utils.network.huggingface_downloader import HuggingfaceDownloader
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.windows.setup_wizard.base_wizard import BaseWizard
from airunner.windows.setup_wizard.installation_settings.templates.install_page_ui import Ui_install_page

nltk.data.path.append(NLTK_DOWNLOAD_DIR)

CONTROLNET_PATHS = [
    "lllyasviel/control_v11p_sd15_canny",
    "lllyasviel/control_v11f1p_sd15_depth",
    "lllyasviel/control_v11f1p_sd15_depth",
    "lllyasviel/control_v11f1p_sd15_depth",
    "lllyasviel/control_v11f1p_sd15_depth",
    "lllyasviel/control_v11p_sd15_mlsd",
    "lllyasviel/control_v11p_sd15_normalbae",
    "lllyasviel/control_v11p_sd15_normalbae",
    "lllyasviel/control_v11p_sd15_scribble",
    "lllyasviel/control_v11p_sd15_scribble",
    "lllyasviel/control_v11p_sd15_seg",
    "lllyasviel/control_v11p_sd15_lineart",
    "lllyasviel/control_v11p_sd15_lineart",
    "lllyasviel/control_v11p_sd15s2_lineart_anime",
    "lllyasviel/control_v11p_sd15_openpose",
    "lllyasviel/control_v11p_sd15_openpose",
    "lllyasviel/control_v11p_sd15_openpose",
    "lllyasviel/control_v11p_sd15_openpose",
    "lllyasviel/control_v11p_sd15_openpose",
    "lllyasviel/control_v11p_sd15_softedge",
    "lllyasviel/control_v11p_sd15_softedge",
    "lllyasviel/control_v11p_sd15_softedge",
    "lllyasviel/control_v11p_sd15_softedge",
    "lllyasviel/control_v11e_sd15_ip2p",
    "lllyasviel/control_v11p_sd15_inpaint",
    "lllyasviel/control_v11e_sd15_shuffle",
]


class InstallWorker(
    QObject,
    MediatorMixin,
    SettingsMixin
):
    file_download_finished = Signal()
    progress_updated = Signal(int, int)

    def __init__(self, parent, setup_settings):
        super(InstallWorker, self).__init__()
        self.parent = parent
        self.setup_settings = setup_settings
        self.total_models_in_current_step = 0
        self.hf_downloader = HuggingfaceDownloader(
            lambda a, b: self.progress_updated.emit(a, b)
        )
        self.hf_downloader.completed.connect(
            lambda: self.file_download_finished.emit()
        )
        self.register(SignalCode.DOWNLOAD_COMPLETE, self.download_finished)

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
        if using_custom_model:
            # TODO: test custom case
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
            for action in SD_FILE_BOOTSTRAP_DATA[model_version]:
                for model in model_bootstrap_data:
                    if model["pipeline_action"] != action:
                        continue
                    if model["category"] != "stablediffusion":
                        continue
                    if model["version"] != model_version:
                        continue
                    if model["enabled"] is False:
                        continue

                    # add pipeline_files to models_to_download
                    if action in ["datasets", "safety_checker", "feature_extractor"]:
                        requested_file_path = os.path.expanduser(
                            os.path.join(
                                self.settings["path_settings"][f"{model['pipeline_action']}_model_path"],
                                model["path"]
                            )
                        )
                    else:
                        requested_file_path = os.path.expanduser(
                            os.path.join(
                                self.settings["path_settings"][f"{model['pipeline_action']}_model_path"],
                                model["version"],
                            )
                        )
                    model["files"] = SD_FILE_BOOTSTRAP_DATA[model_version][action]
                    model["requested_file_path"] = requested_file_path
                    models_to_download.append(model)
                    self.total_models_in_current_step += len(model["files"])
                    self.parent.total_steps += len(model["files"])

            for model in models_to_download:
                for filename in model["files"]:
                    try:
                        self.hf_downloader.download_model(
                            requested_path=model["path"],
                            requested_file_name=filename,
                            requested_file_path=model["requested_file_path"],
                            requested_callback=self.progress_updated.emit
                        )
                    except Exception as e:
                        print(f"Error downloading {filename}: {e}")

    def download_controlnet(self):
        self.parent.set_status("Downloading Controlnet models...")
        model_version = self.setup_settings["model_version"]

        controlnet_files = SD_FILE_BOOTSTRAP_DATA[model_version]["controlnet"]
        total_controlnet_files = len(CONTROLNET_PATHS * len(controlnet_files))
        self.total_models_in_current_step += total_controlnet_files

        if total_controlnet_files == 0:
            self.download_finished()
            return

        for path in CONTROLNET_PATHS:
            for filename in controlnet_files:
                try:
                    requested_file_path = os.path.expanduser(
                        os.path.join(
                            self.settings["path_settings"][f"controlnet_model_path"],
                            path
                        )
                    )
                    self.hf_downloader.download_model(
                        requested_path=path,
                        requested_file_name=filename,
                        requested_file_path=requested_file_path,
                        requested_callback=self.progress_updated.emit
                    )
                except Exception as e:
                    print(f"Error downloading {filename}: {e}")

    def download_llms(self):
        if self.setup_settings["enable_llm"]:
            self.parent.set_status("Downloading LLM models...")
            for k, v in LLM_FILE_BOOTSTRAP_DATA.items():
                self.total_models_in_current_step += len(v["files"])

            for k, v in LLM_FILE_BOOTSTRAP_DATA.items():
                for filename in v["files"]:
                    try:
                        requested_file_path = os.path.expanduser(
                            os.path.join(
                                self.settings["path_settings"][v["path_settings"]],
                                k
                            )
                        )
                        self.hf_downloader.download_model(
                            requested_path=k,
                            requested_file_name=filename,
                            requested_file_path=requested_file_path,
                            requested_callback=self.progress_updated.emit
                        )
                    except Exception as e:
                        print(f"Error downloading {filename}: {e}")

    def download_stt(self):
        if self.setup_settings["enable_stt"]:
            self.parent.set_status("Downloading STT models...")
            for k, v in WHISPER_FILES.items():
                self.total_models_in_current_step += len(v)
            for k, v in WHISPER_FILES.items():
                for filename in v:
                    requested_file_path = os.path.expanduser(
                        os.path.join(
                            self.settings["path_settings"]["stt_model_path"],
                            k
                        )
                    )
                    try:
                        self.hf_downloader.download_model(
                            requested_path=k,
                            requested_file_name=filename,
                            requested_file_path=requested_file_path,
                            requested_callback=self.progress_updated.emit
                        )
                    except Exception as e:
                        print(f"Error downloading {filename}: {e}")

    def download_tts(self):
        if self.setup_settings["enable_tts"]:
            self.parent.set_status("Downloading TTS models...")
            for k, v in SPEECH_T5_FILES.items():
                self.total_models_in_current_step += len(v)

            for k, v in SPEECH_T5_FILES.items():
                for filename in v:
                    requested_file_path = os.path.expanduser(
                        os.path.join(
                            self.settings["path_settings"]["tts_model_path"],
                            k
                        )
                    )
                    try:
                        self.hf_downloader.download_model(
                            requested_path=k,
                            requested_file_name=filename,
                            requested_file_path=requested_file_path,
                            requested_callback=self.progress_updated.emit
                        )
                    except Exception as e:
                        print(f"Error downloading {filename}: {e}")

    def download_nltk_files(self):
        self.parent.set_status("Downloading NLTK files...")
        nltk.download(
            "stopwords",
            download_dir=NLTK_DOWNLOAD_DIR,
            quiet=True,
            halt_on_error=False,
            raise_on_error=False
        )
        nltk.download(
            "punkt",
            download_dir=NLTK_DOWNLOAD_DIR,
            quiet=True,
            halt_on_error=False,
            raise_on_error=False
        )
        self.download_finished()

    def finalize_installation(self):
        self.parent.set_status("Installation complete.")
        self.parent.update_progress_bar()
        self.parent.parent.show_final_page()

    def update_progress(self, current, total):
        print("update progress", current, total)

    @Slot()
    def download_finished(self, _data: dict = None):
        self.total_models_in_current_step -= 1
        if self.total_models_in_current_step <= 0:
            self.set_page()

    def run(self):
        if (
            self.setup_settings["user_agreement_completed"] and
            self.setup_settings["airunner_license_completed"]
        ):
            self.current_step = -1
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
            self.current_step is -1
        ):
            self.parent.set_status(f"Downloading {model_path}...")
            print(f"Dowloading {model_path}...")
            self.current_step = 0
            self.download_stable_diffusion()
        elif (
            self.setup_settings["enable_sd"] and
            self.setup_settings["sd_license_completed"] and
            self.setup_settings["enable_controlnet"] and
            self.current_step == 0
        ):
            self.current_step = 1
            self.download_controlnet()
        elif self.setup_settings["enable_llm"] and self.current_step < 2:
            self.current_step = 2
            self.download_llms()
        elif self.setup_settings["enable_tts"] and self.current_step < 3:
            self.current_step = 3
            self.download_tts()
        elif self.setup_settings["enable_stt"] and self.current_step < 4:
            self.current_step = 4
            self.download_stt()
        elif self.current_step < 5:
            self.current_step = 5
            self.download_nltk_files()
        else:
            self.current_step = 6
            self.finalize_installation()


class InstallPage(BaseWizard):
    class_name_ = Ui_install_page

    def __init__(self, parent, setup_settings):
        super(InstallPage, self).__init__(parent)
        self.steps_completed = 0
        self.setup_settings = setup_settings

        # reset the progress bar
        self.ui.progress_bar.setValue(0)
        self.ui.progress_bar.setMaximum(100)

        # These will increase
        self.total_steps = 0
        if self.setup_settings["enable_sd"] and self.setup_settings["sd_license_completed"]:
            self.total_steps += 1
        if self.setup_settings["enable_controlnet"]:
            self.total_steps += len(CONTROLNET_PATHS) * len(SD_FILE_BOOTSTRAP_DATA[self.setup_settings["model_version"]]["controlnet"])
        if self.setup_settings["enable_llm"]:
            for k, v in LLM_FILE_BOOTSTRAP_DATA.items():
                self.total_steps += len(v)
        if self.setup_settings["enable_tts"]:
            for k, v in SPEECH_T5_FILES.items():
                self.total_steps += len(v)
        if self.setup_settings["enable_stt"]:
            for k, v in WHISPER_FILES.items():
                self.total_steps += len(v)

        self.register(SignalCode.DOWNLOAD_COMPLETE, self.update_progress_bar)
        self.register(SignalCode.DOWNLOAD_PROGRESS, self.download_progress)
        self.register(SignalCode.UPDATE_DOWNLOAD_LOG, self.update_download_log)
        self.register(SignalCode.CLEAR_DOWNLOAD_STATUS_BAR, self.clear_status_bar)
        self.register(SignalCode.SET_DOWNLOAD_STATUS_LABEL, self.on_set_download_status_label)

        self.thread = QThread()
        self.worker = InstallWorker(self, setup_settings)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    def download_progress(self, data: dict):
        if data["current"] == 0:
            progress = 0
        else:
            progress = data["current"] / data["total"]
        self.ui.status_bar.setValue(progress * 100)

    def update_progress_bar(self, _data: dict = None):
        self.steps_completed += 1
        if self.total_steps == self.steps_completed:
            self.ui.progress_bar.setValue(100)
        else:
            self.ui.progress_bar.setValue((self.steps_completed / self.total_steps) * 100)

    def set_status(self, message: str):
        # set the text of a QProgressBar
        self.ui.status_bar.setFormat(message)

    def update_download_log(self, data: dict):
        self.ui.log.appendPlainText(data["message"]+"\n")

    def clear_status_bar(self, _data: dict):
        self.ui.status.setText("")
        self.ui.status_bar.setValue(0)

    def on_set_download_status_label(self, data):
        self.ui.status.setText(data["message"])
