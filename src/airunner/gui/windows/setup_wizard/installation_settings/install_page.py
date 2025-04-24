from typing import List, Dict
import os.path

from PySide6.QtCore import QObject, QThread, Slot, Signal

from airunner.data.models import AIModels, ControlnetModel
from airunner.data.bootstrap.model_bootstrap_data import model_bootstrap_data
from airunner.data.bootstrap.controlnet_bootstrap_data import (
    controlnet_bootstrap_data,
)
from airunner.data.bootstrap.sd_file_bootstrap_data import (
    SD_FILE_BOOTSTRAP_DATA,
)
from airunner.data.bootstrap.flux_file_bootstrap_data import (
    FLUX_FILE_BOOTSTRAP_DATA,
)
from airunner.data.bootstrap.llm_file_bootstrap_data import (
    LLM_FILE_BOOTSTRAP_DATA,
)
from airunner.data.bootstrap.whisper import WHISPER_FILES
from airunner.data.bootstrap.speech_t5 import SPEECH_T5_FILES
from airunner.enums import SignalCode
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.utils.network import HuggingfaceDownloader
from airunner.utils.os import create_airunner_paths
from airunner.gui.windows.main.settings_mixin import SettingsMixin
from airunner.gui.windows.setup_wizard.base_wizard import BaseWizard
from airunner.gui.windows.setup_wizard.installation_settings.templates.install_page_ui import (
    Ui_install_page,
)


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
    MediatorMixin,
    SettingsMixin,
    QObject,
):
    file_download_finished = Signal()
    progress_updated = Signal(int, int)

    def __init__(self, parent, models_enabled: List[str]):
        super().__init__()
        self.parent = parent
        self.models_enabled = models_enabled
        self.current_step = -1
        self.total_models_in_current_step = 0
        self.hf_downloader = HuggingfaceDownloader(
            lambda a, b: self.progress_updated.emit(a, b)
        )
        self.hf_downloader.completed.connect(
            lambda: self.file_download_finished.emit()
        )
        self.register(SignalCode.DOWNLOAD_COMPLETE, self.download_finished)
        self.register(SignalCode.PATH_SET, self.path_set)

    def download_stable_diffusion(self):
        if not self.models_enabled["stable_diffusion"]:
            self.set_page()
            return
        self.parent.on_set_downloading_status_label(
            {"label": "Downloading Stable Diffusion models..."}
        )

        models = model_bootstrap_data

        self.total_models_in_current_step += len(models)
        for model in models:
            if model["name"] == "CompVis Safety Checker":
                action_key = "safety_checker"
                action = f"{model['pipeline_action']}/{action_key}"
            elif model["name"] == "OpenAI Feature Extractor":
                action_key = "feature_extractor"
                action = f"{model['pipeline_action']}/{action_key}"
            else:
                action = model["pipeline_action"]
                action_key = model["pipeline_action"]
            if not self.models_enabled.get(action, True):
                continue
            try:
                files = SD_FILE_BOOTSTRAP_DATA[model["version"]][action_key]
            except KeyError:
                continue
            self.parent.total_steps += len(files)
            for filename in files:
                requested_file_path = os.path.expanduser(
                    os.path.join(
                        self.path_settings.base_path,
                        model["model_type"],
                        "models",
                        model["version"],
                        action,
                    )
                )
                try:
                    self.hf_downloader.download_model(
                        requested_path=model["path"],
                        requested_file_name=filename,
                        requested_file_path=requested_file_path,
                        requested_callback=self.progress_updated.emit,
                    )
                except Exception as e:
                    print(f"Error downloading {filename}: {e}")

    def download_controlnet(self):
        if not self.models_enabled["stable_diffusion"]:
            self.set_page()
            return
        self.parent.on_set_downloading_status_label(
            {"label": "Downloading Controlnet models..."}
        )
        self.total_models_in_current_step += len(controlnet_bootstrap_data)
        for controlnet_model in controlnet_bootstrap_data:
            if not self.models_enabled.get(controlnet_model["name"], True):
                continue
            files = SD_FILE_BOOTSTRAP_DATA[controlnet_model["version"]][
                "controlnet"
            ]
            self.parent.total_steps += len(files)
            for filename in files:
                requested_file_path = os.path.expanduser(
                    os.path.join(
                        self.path_settings.base_path,
                        "art",
                        "models",
                        controlnet_model["version"],
                        "controlnet",
                        controlnet_model["path"],
                    )
                )
                try:
                    self.hf_downloader.download_model(
                        requested_path=controlnet_model["path"],
                        requested_file_name=filename,
                        requested_file_path=requested_file_path,
                        requested_callback=self.progress_updated.emit,
                    )
                except Exception as e:
                    print(f"Error downloading {filename}: {e}")

    def download_flux(self):
        self.parent.on_set_downloading_status_label(
            {"label": "Downloading Flux files..."}
        )

        models = model_bootstrap_data

        self.total_models_in_current_step += len(models)
        for model in models:
            action = model["pipeline_action"]
            try:
                files = FLUX_FILE_BOOTSTRAP_DATA[model["version"]]
            except KeyError:
                continue
            self.parent.total_steps += len(files)
            for filename in files:
                requested_file_path = os.path.expanduser(
                    os.path.join(
                        self.path_settings.base_path,
                        model["model_type"],
                        "models",
                        model["version"],
                        action,
                    )
                )
                try:
                    self.hf_downloader.download_model(
                        requested_path=model["path"],
                        requested_file_name=filename,
                        requested_file_path=requested_file_path,
                        requested_callback=self.progress_updated.emit,
                    )
                except Exception as e:
                    print(f"Error downloading {filename}: {e}")

    def download_controlnet_processors(self):
        if not self.models_enabled["stable_diffusion"]:
            self.set_page()
            return
        self.parent.on_set_downloading_status_label(
            {"label": "Downloading Controlnet processors..."}
        )
        controlnet_processor_files = [
            "150_16_swin_l_oneformer_coco_100ep.pth",
            "250_16_swin_l_oneformer_ade20k_160k.pth",
            "ControlNetHED.pth",
            "ControlNetLama.pth",
            "RealESRGAN_x4plus.pth",
            "ZoeD_M12_N.pt",
            "body_pose_model.pth",
            "clip_g.pth",
            "dpt_hybrid-midas-501f0c75.pt",
            "erika.pth",
            "facenet.pth",
            "hand_pose_model.pth",
            "lama.ckpt",
            "latest_net_G.pth",
            "mlsd_large_512_fp32.pth",
            "netG.pth",
            "network-bsds500.pth",
            "res101.pth",
            "scannet.pt",
            "sk_model.pth",
            "sk_model2.pth",
            "table5_pidinet.pth",
            "upernet_global_small.pth",
        ]
        self.parent.total_steps += len(controlnet_processor_files)
        for filename in controlnet_processor_files:
            requested_file_path = os.path.expanduser(
                os.path.join(
                    self.path_settings.base_path,
                    "art",
                    "models",
                    "controlnet_processors",
                )
            )
            try:
                self.hf_downloader.download_model(
                    requested_path=f"lllyasviel/Annotators",
                    requested_file_name=filename,
                    requested_file_path=requested_file_path,
                    requested_callback=self.progress_updated.emit,
                )
            except Exception as e:
                print(f"Error downloading {filename}: {e}")

    def download_llms(self):
        if not self.models_enabled["mistral"]:
            self.set_page()
            return

        models = []
        for model in model_bootstrap_data:
            if model["category"] == "llm":
                if model["pipeline_action"] == "embedding":
                    if not self.models_enabled["embedding_model"]:
                        continue
                else:
                    if not self.models_enabled["mistral"]:
                        continue
                models.append(model)
        self.total_models_in_current_step += len(models)
        for model in models:
            files = LLM_FILE_BOOTSTRAP_DATA[model["path"]]["files"]
            self.parent.total_steps += len(files)
            for filename in files:
                requested_file_path = os.path.expanduser(
                    os.path.join(
                        self.path_settings.base_path,
                        "text",
                        "models",
                        model["category"],
                        model["pipeline_action"],
                        model["path"],
                    )
                )
                try:
                    self.hf_downloader.download_model(
                        requested_path=model["path"],
                        requested_file_name=filename,
                        requested_file_path=requested_file_path,
                        requested_callback=self.progress_updated.emit,
                    )
                except Exception as e:
                    print(f"Error downloading {filename}: {e}")

    def download_stt(self):
        if not self.models_enabled["whisper"]:
            self.set_page()
            return
        self.parent.on_set_downloading_status_label(
            {"label": "Downloading STT models..."}
        )
        for k, v in WHISPER_FILES.items():
            self.total_models_in_current_step += len(v)
        for k, v in WHISPER_FILES.items():
            for filename in v:
                requested_file_path = os.path.expanduser(
                    os.path.join(
                        self.path_settings.base_path,
                        "text",
                        "models",
                        "stt",
                        k,
                    )
                )
                try:
                    self.hf_downloader.download_model(
                        requested_path=k,
                        requested_file_name=filename,
                        requested_file_path=requested_file_path,
                        requested_callback=self.progress_updated.emit,
                    )
                except Exception as e:
                    print(f"Error downloading {filename}: {e}")

    def download_tts(self):
        if not self.models_enabled["speecht5"]:
            self.set_page()
            return
        self.parent.on_set_downloading_status_label(
            {"label": "Downloading TTS models..."}
        )
        for k, v in SPEECH_T5_FILES.items():
            self.total_models_in_current_step += len(v)
            for filename in v:
                requested_file_path = os.path.expanduser(
                    os.path.join(
                        self.path_settings.base_path,
                        "text",
                        "models",
                        "tts",
                        k,
                    )
                )
                try:
                    self.hf_downloader.download_model(
                        requested_path=k,
                        requested_file_name=filename,
                        requested_file_path=requested_file_path,
                        requested_callback=self.progress_updated.emit,
                    )
                except Exception as e:
                    print(f"Error downloading {filename}: {e}")

    def finalize_installation(self, *_args):
        self.parent.on_set_downloading_status_label(
            {"label": "Installation complete."}
        )
        self.parent.update_progress_bar(final=True)

    @staticmethod
    def update_progress(current, total):
        print("update progress", current, total)

    @Slot()
    def download_finished(self):
        self.total_models_in_current_step -= 1
        if self.total_models_in_current_step <= 0:
            self.set_page()

    @Slot()
    def path_set(self):
        self.set_page()

    def run(self):
        if (
            self.application_settings.user_agreement_checked
            and self.application_settings.stable_diffusion_agreement_checked
            and self.application_settings.airunner_agreement_checked
        ):
            self.current_step = -1
            self.set_page()

    def set_page(self):
        if (
            self.application_settings.stable_diffusion_agreement_checked
            and self.current_step == -1
        ):
            """
            Create the airunner paths
            """
            create_airunner_paths(self.path_settings)
            self.update_application_settings("paths_initialized", True)
            self.parent.on_set_downloading_status_label(
                {"label": f"Downloading Stable Diffusion"}
            )
            self.current_step = 1
            self.download_stable_diffusion()
        elif (
            self.application_settings.stable_diffusion_agreement_checked
            and self.current_step == 1
        ):
            self.parent.on_set_downloading_status_label(
                {"label": f"Downloading Controlnet"}
            )
            self.current_step = 2
            self.download_controlnet()
        elif (
            self.application_settings.stable_diffusion_agreement_checked
            and self.current_step == 2
        ):
            self.current_step = 3
            self.download_controlnet_processors()
        elif self.current_step == 3:
            self.current_step = 4
            self.download_flux()
        elif self.current_step == 4:
            self.parent.on_set_downloading_status_label(
                {"label": f"Downloading LLM"}
            )
            self.current_step = 5
            self.download_llms()
        elif self.current_step == 5:
            self.parent.on_set_downloading_status_label(
                {"label": f"Downloading Text-to-Speech"}
            )
            self.current_step = 6
            self.download_tts()
        elif self.current_step == 6:
            self.parent.on_set_downloading_status_label(
                {"label": f"Downloading Speech-to-Text"}
            )
            self.current_step = 7
            self.download_stt()
        elif self.current_step == 7:
            self.hf_downloader.download_model(
                requested_path="",
                requested_file_name="",
                requested_file_path="",
                requested_callback=self.finalize_installation,
            )


class InstallPage(BaseWizard):
    class_name_ = Ui_install_page

    def __init__(
        self,
        parent,
        stablediffusion_models: List[Dict[str, str]],
        models_enabled: List[str],
    ):
        super(InstallPage, self).__init__(parent)
        self.stablediffusion_models = stablediffusion_models
        self.models_enabled = models_enabled
        self.steps_completed = 0

        # reset the progress bar
        self.ui.progress_bar.setValue(0)
        self.ui.progress_bar.setMaximum(100)

        # These will increase
        self.total_steps = 0

        self.total_steps += len(SD_FILE_BOOTSTRAP_DATA["SD 1.5"]["txt2img"])
        self.total_steps += len(SD_FILE_BOOTSTRAP_DATA["SD 1.5"]["inpaint"])

        # Determine total controlnet models being downloaded
        if self.models_enabled["safety_checker"]:
            self.total_steps += len(
                SD_FILE_BOOTSTRAP_DATA["SD 1.5"]["safety_checker"]
            )

        if self.models_enabled["feature_extractor"]:
            self.total_steps += len(
                SD_FILE_BOOTSTRAP_DATA["SD 1.5"]["feature_extractor"]
            )

        # Controlnet models
        for model in self.stablediffusion_models:
            if model["name"] in (
                "safety_checker",
                "feature_extractor",
            ):
                continue
            if self.models_enabled[model["name"]]:
                self.total_steps += len(
                    SD_FILE_BOOTSTRAP_DATA[model["version"]][
                        model["pipeline_action"]
                    ]
                )

        # Increase total number of LLMs downloaded
        if self.models_enabled["mistral"]:
            self.total_steps += len(
                LLM_FILE_BOOTSTRAP_DATA[
                    "w4ffl35/Ministral-8B-Instruct-2410-doublequant"
                ]["files"]
            )

        if self.models_enabled["speecht5"]:
            self.total_steps += len(SPEECH_T5_FILES["microsoft/speecht5_tts"])

        if self.models_enabled["whisper"]:
            self.total_steps += len(WHISPER_FILES["openai/whisper-tiny"])

        if self.models_enabled["embedding_model"]:
            self.total_steps += len(
                LLM_FILE_BOOTSTRAP_DATA["intfloat/e5-large"]["files"]
            )

        self.register(SignalCode.DOWNLOAD_COMPLETE, self.update_progress_bar)
        self.register(SignalCode.DOWNLOAD_PROGRESS, self.download_progress)
        self.register(SignalCode.UPDATE_DOWNLOAD_LOG, self.update_download_log)
        self.register(
            SignalCode.CLEAR_DOWNLOAD_STATUS_BAR, self.clear_status_bar
        )
        self.register(
            SignalCode.SET_DOWNLOAD_STATUS_LABEL,
            self.on_set_downloading_status_label,
        )

        self.thread = QThread()
        self.worker = InstallWorker(self, models_enabled=self.models_enabled)
        self.worker.moveToThread(self.thread)

    def start(self):
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    def on_set_downloading_status_label(self, data: dict = None):
        if "message" in data:
            self.set_status(data["message"])

        if "label" in data:
            self.ui.status_bar.setFormat(data["label"])

    def download_progress(self, data: dict):
        if data["current"] == 0:
            progress = 0
        else:
            progress = data["current"] / data["total"]
        self.ui.status_bar.setValue(progress * 100)

    def update_progress_bar(self, final: bool = False):
        if final:
            self.steps_completed = self.total_steps
        else:
            self.steps_completed += 1
        if self.total_steps == self.steps_completed:
            self.ui.progress_bar.setValue(100)
        else:
            self.ui.progress_bar.setValue(
                (self.steps_completed / self.total_steps) * 100
            )

    def set_status(self, message: str):
        # set the text of a QProgressBar
        self.ui.status_bar.setFormat(message)

    def update_download_log(self, data: dict):
        self.ui.log.appendPlainText(data["message"] + "\n")

    def clear_status_bar(self):
        self.ui.status.setText("")
        self.ui.status_bar.setValue(0)
