import os.path

import nltk
from PySide6.QtCore import QObject, QThread, Slot, Signal
from sqlalchemy import func

from airunner.data.models import AIModels, ControlnetModel
from airunner.data.bootstrap.model_bootstrap_data import model_bootstrap_data
from airunner.data.bootstrap.controlnet_bootstrap_data import controlnet_bootstrap_data
from airunner.data.bootstrap.sd_file_bootstrap_data import SD_FILE_BOOTSTRAP_DATA
from airunner.data.bootstrap.tiny_autoencoder import TINY_AUTOENCODER_FILES_SD, TINY_AUTOENCODER_FILES_SDXL
from airunner.data.bootstrap.llm_file_bootstrap_data import LLM_FILE_BOOTSTRAP_DATA
from airunner.data.bootstrap.whisper import WHISPER_FILES
from airunner.data.bootstrap.speech_t5 import SPEECH_T5_FILES
from airunner.enums import SignalCode
from airunner.mediator_mixin import MediatorMixin
from airunner.settings import NLTK_DOWNLOAD_DIR
from airunner.utils.network.huggingface_downloader import HuggingfaceDownloader
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.windows.setup_wizard.base_wizard import BaseWizard
from airunner.windows.setup_wizard.installation_settings.templates.install_page_ui import Ui_install_page
from airunner.utils.os.create_airunner_directory import create_airunner_paths

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

    def __init__(self, parent):
        MediatorMixin.__init__(self)
        
        super(InstallWorker, self).__init__()
        self.parent = parent
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
        self.parent.on_set_downloading_status_label({
            "label": "Downloading Stable Diffusion models..."
        })

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
            try:
                files = SD_FILE_BOOTSTRAP_DATA[model['version']][action_key]
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
                        action
                    )
                )
                try:
                    self.hf_downloader.download_model(
                        requested_path=model["path"],
                        requested_file_name=filename,
                        requested_file_path=requested_file_path,
                        requested_callback=self.progress_updated.emit
                    )
                except Exception as e:
                    print(f"Error downloading {filename}: {e}")
    
    def download_tiny_autoencoders(self):
        self.parent.on_set_downloading_status_label({
            "label": "Downloading Tiny Autoencoders..."
        })
        self.total_models_in_current_step += len(TINY_AUTOENCODER_FILES_SD["madebyollin/taesd"])
        self.total_models_in_current_step += len(TINY_AUTOENCODER_FILES_SDXL["madebyollin/sdxl-vae-fp16-fix"])
        for k, v in TINY_AUTOENCODER_FILES_SD.items():
            for filename in v:
                requested_file_path = os.path.expanduser(
                    os.path.join(
                        self.path_settings.base_path,
                        "art",
                        "models",
                        "SD 1.5",
                        "tiny_autoencoder",
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
        for k, v in TINY_AUTOENCODER_FILES_SDXL.items():
            for filename in v:
                requested_file_path = os.path.expanduser(
                    os.path.join(
                        self.path_settings.base_path,
                        "art",
                        "models",
                        "SDXL 1.0",
                        "tiny_autoencoder",
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

    def download_controlnet(self):
        self.parent.on_set_downloading_status_label({
            "label": "Downloading Controlnet models..."
        })
        self.total_models_in_current_step += len(controlnet_bootstrap_data)
        for controlnet_model in controlnet_bootstrap_data:
            files = SD_FILE_BOOTSTRAP_DATA[controlnet_model["version"]]["controlnet"]
            self.parent.total_steps += len(files)
            for filename in files:
                requested_file_path = os.path.expanduser(
                    os.path.join(
                        self.path_settings.base_path,
                        "art",
                        "models",
                        controlnet_model["version"],
                        "controlnet",
                        controlnet_model["path"]
                    )
                )
                try:
                    self.hf_downloader.download_model(
                        requested_path=controlnet_model["path"],
                        requested_file_name=filename,
                        requested_file_path=requested_file_path,
                        requested_callback=self.progress_updated.emit
                    )
                except Exception as e:
                    print(f"Error downloading {filename}: {e}")

    def download_controlnet_processors(self):
        self.parent.on_set_downloading_status_label({
            "label": "Downloading Controlnet processors..."
        })
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
                    "controlnet_processors"
                )
            )
            try:
                self.hf_downloader.download_model(
                    requested_path=f"lllyasviel/Annotators",
                    requested_file_name=filename,
                    requested_file_path=requested_file_path,
                    requested_callback=self.progress_updated.emit
                )
            except Exception as e:
                print(f"Error downloading {filename}: {e}")

    def download_llms(self):
        models = [model for model in model_bootstrap_data if model["category"] == "llm"]
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
                        model["path"]
                    )
                )
                try:
                    self.hf_downloader.download_model(
                        requested_path=model["path"],
                        requested_file_name=filename,
                        requested_file_path=requested_file_path,
                        requested_callback=self.progress_updated.emit
                    )
                except Exception as e:
                    print(f"Error downloading {filename}: {e}")

    def download_stt(self):
        self.parent.on_set_downloading_status_label({
            "label": "Downloading STT models..."
        })
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
        self.parent.on_set_downloading_status_label({
            "label": "Downloading TTS models..."
        })
        for k, v in SPEECH_T5_FILES.items():
            self.total_models_in_current_step += len(v)
            for filename in v:
                requested_file_path = os.path.expanduser(
                    os.path.join(
                        self.path_settings.base_path,
                        "text",
                        "models",
                        "tts",
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
        self.parent.on_set_downloading_status_label({
            "label": "Downloading NLTK models..."
        })
        path = os.path.expanduser(os.path.join(
            NLTK_DOWNLOAD_DIR,
            "corpora"
        ))
        os.makedirs(path, exist_ok=True)
        path = os.path.expanduser(os.path.join(
            NLTK_DOWNLOAD_DIR,
            "tokenizers",
            "punkt"
        ))
        os.makedirs(path, exist_ok=True)
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

    def finalize_installation(self, *args):
        self.parent.on_set_downloading_status_label({
            "label": "Installation complete."
        })
        self.parent.update_progress_bar()
        self.parent.parent.show_final_page()

    def update_progress(self, current, total):
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
            self.application_settings.user_agreement_checked and
            self.application_settings.stable_diffusion_agreement_checked and
            self.application_settings.airunner_agreement_checked
        ):
            self.current_step = -1
            self.set_page()

    def set_page(self):
        if (
            self.application_settings.stable_diffusion_agreement_checked and
            self.current_step == -1
        ):
            """
            Create the airunner paths
            """
            create_airunner_paths(self.path_settings)
            self.update_application_settings("paths_initialized", True)
            self.parent.on_set_downloading_status_label({
                "label": f"Downloading Stable Diffusion"
            })
            self.current_step = 1
            self.download_stable_diffusion()
            self.download_tiny_autoencoders()
        elif (
            self.application_settings.stable_diffusion_agreement_checked and
            self.current_step == 1
        ):
            self.parent.on_set_downloading_status_label({
                "label": f"Downloading Controlnet"
            })
            self.current_step = 2
            self.download_controlnet()
        elif (
            self.application_settings.stable_diffusion_agreement_checked and
            self.current_step == 2
        ):
            self.current_step = 3
            self.download_controlnet_processors()
        elif self.current_step == 3:
            self.parent.on_set_downloading_status_label({
                "label": f"Downloading LLM"
            })
            self.current_step = 4
            self.download_llms()
        elif self.current_step == 4:
            self.parent.on_set_downloading_status_label({
                "label": f"Downloading Text-to-Speech"
            })
            self.current_step = 5
            self.download_tts()
        elif self.current_step == 5:
            self.parent.on_set_downloading_status_label({
                "label": f"Downloading NLTK files"
            })
            self.current_step = 6
            self.download_nltk_files()
        elif self.current_step == 6:
            self.parent.on_set_downloading_status_label({
                "label": f"Downloading Speech-to-Text"
            })
            self.current_step = 7
            self.download_stt()
        elif self.current_step == 7:
             self.hf_downloader.download_model(
                 requested_path="",
                 requested_file_name="",
                 requested_file_path="",
                 requested_callback=self.finalize_installation
             )


class InstallPage(BaseWizard):
    class_name_ = Ui_install_page

    def __init__(self, parent):
        super(InstallPage, self).__init__(parent)
        self.steps_completed = 0

        # reset the progress bar
        self.ui.progress_bar.setValue(0)
        self.ui.progress_bar.setMaximum(100)

        # These will increase
        self.total_steps = 0
        if self.application_settings.stable_diffusion_agreement_checked:
            self.total_steps += 1

        controlnet_model_ids = ControlnetModel.objects.distinct(ControlnetModel.id).all()
        controlnet_model_count = len(controlnet_model_ids)

        controlnet_model_versions = ControlnetModel.objects.distinct(ControlnetModel.version).all()
        controlnet_version_count = len(controlnet_model_versions)

        llm_model_count_query = AIModels.objects.filter(AIModels.category == 'llm').all()
        llm_model_count = len(llm_model_count_query)

        self.total_steps += controlnet_model_count * controlnet_version_count
        self.total_steps += len(TINY_AUTOENCODER_FILES_SD["madebyollin/taesd"])
        self.total_steps += len(TINY_AUTOENCODER_FILES_SDXL["madebyollin/sdxl-vae-fp16-fix"])
        self.total_steps += llm_model_count
        self.total_steps += len(SPEECH_T5_FILES["microsoft/speecht5_tts"])
        self.total_steps += len(WHISPER_FILES["openai/whisper-tiny"])

        self.register(SignalCode.DOWNLOAD_COMPLETE, self.update_progress_bar)
        self.register(SignalCode.DOWNLOAD_PROGRESS, self.download_progress)
        self.register(SignalCode.UPDATE_DOWNLOAD_LOG, self.update_download_log)
        self.register(SignalCode.CLEAR_DOWNLOAD_STATUS_BAR, self.clear_status_bar)
        self.register(SignalCode.SET_DOWNLOAD_STATUS_LABEL, self.on_set_downloading_status_label)

        self.thread = QThread()
        self.worker = InstallWorker(self)
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

    def update_progress_bar(self):
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

    def clear_status_bar(self):
        self.ui.status.setText("")
        self.ui.status_bar.setValue(0)
