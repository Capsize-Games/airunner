from typing import List, Dict
import importlib.util
import os.path
import sys
import zipfile

try:
    import requests
except ImportError:
    requests = None

try:
    import nltk
except ImportError:
    nltk = None

from PySide6.QtCore import QObject, QThread, Slot, Signal, QTimer
from PySide6.QtWidgets import QWizard

from airunner.components.data.bootstrap.model_bootstrap_data import model_bootstrap_data
from airunner.components.art.data.bootstrap.controlnet_bootstrap_data import (
    controlnet_bootstrap_data,
)
from airunner.components.art.data.bootstrap.sd_file_bootstrap_data import (
    SD_FILE_BOOTSTRAP_DATA,
)
from airunner.components.tts.data.bootstrap.openvoice_bootstrap_data import OPENVOICE_FILES
from airunner.components.art.data.bootstrap.flux_file_bootstrap_data import (
    FLUX_FILE_BOOTSTRAP_DATA,
)
from airunner.components.llm.data.bootstrap.llm_file_bootstrap_data import (
    LLM_FILE_BOOTSTRAP_DATA,
)
from airunner.components.stt.data.bootstrap.whisper import WHISPER_FILES
from airunner.components.tts.data.bootstrap.speech_t5 import SPEECH_T5_FILES
from airunner.enums import SignalCode
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.utils.network import HuggingfaceDownloader
from airunner.utils.os import create_airunner_paths
from airunner.components.application.gui.windows.main.settings_mixin import SettingsMixin
from airunner.components.downloader.gui.windows.setup_wizard.base_wizard import BaseWizard
from airunner.components.downloader.gui.windows.setup_wizard.installation_settings.templates.install_page_ui import (
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


class InstallWorker(
    MediatorMixin,
    SettingsMixin,
    QObject,
):
    file_download_finished = Signal()
    progress_updated = Signal(int, int)

    def __init__(self, parent, models_enabled: List[str], initialize_gui=True):
        super().__init__()
        self.parent = parent
        self.total_files = 0
        self.models_enabled = models_enabled
        self.current_step = -1
        self.total_models_in_current_step = 0
        self.hf_downloader = HuggingfaceDownloader(
            lambda a, b: self.progress_updated.emit(a, b),
            initialize_gui=initialize_gui,
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
            self.total_models_in_current_step += len(files)

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
        for controlnet_model in controlnet_bootstrap_data:
            if not self.models_enabled.get(controlnet_model["name"], True):
                continue
            files = SD_FILE_BOOTSTRAP_DATA[controlnet_model["version"]][
                "controlnet"
            ]
            self.parent.total_steps += len(files)
            self.total_models_in_current_step += len(files)
        for controlnet_model in controlnet_bootstrap_data:
            if not self.models_enabled.get(controlnet_model["name"], True):
                continue
            files = SD_FILE_BOOTSTRAP_DATA[controlnet_model["version"]][
                "controlnet"
            ]
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

        for model in models:
            action = model["pipeline_action"]
            try:
                files = FLUX_FILE_BOOTSTRAP_DATA[model["version"]]
            except KeyError:
                continue
            self.parent.total_steps += len(files)
            self.total_models_in_current_step += len(files)
        print(f"Downloading {self.total_models_in_current_step} Flux files")
        for model in models:
            action = model["pipeline_action"]
            try:
                files = FLUX_FILE_BOOTSTRAP_DATA[model["version"]]
            except KeyError:
                continue
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
        self.total_models_in_current_step += len(controlnet_processor_files)
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
                models.append(model)
        for model in models:
            files = LLM_FILE_BOOTSTRAP_DATA[model["path"]]["files"]
            self.parent.total_steps += len(files)
            self.total_models_in_current_step += len(files)
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
                    print("trying to download", filename)
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

        print(f"Downloading {self.total_models_in_current_step} TTS files")

        for k, v in SPEECH_T5_FILES.items():
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

    def download_openvoice(self):
        if not self.models_enabled["openvoice_model"]:
            self.set_page()
            return
        self.parent.on_set_downloading_status_label(
            {"label": "Downloading OpenVoice models..."}
        )
        for k, v in OPENVOICE_FILES.items():
            self.total_models_in_current_step += len(v["files"])
        for k, v in OPENVOICE_FILES.items():
            for filename in v["files"]:
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

    def _download_file_with_progress(self, url, dest_path, label=None):
        """
        Download a file from a direct URL with progress reporting.
        """
        if requests is None:
            raise ImportError(
                "requests library is required for downloading files"
            )

        chunk_size = 8192
        try:
            with requests.get(url, stream=True) as r:
                r.raise_for_status()
                total = int(r.headers.get("content-length", 0))
                downloaded = 0
                with open(dest_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total > 0:
                                self.progress_updated.emit(downloaded, total)
            if label:
                self.parent.update_download_log(
                    {"message": f"Downloaded {label}"}
                )

            # Check if this is an OpenVoice zip file
            if "openvoice" in dest_path and dest_path.endswith(".zip"):
                # Use the special handler for OpenVoice zip downloads
                self.handle_openvoice_zip_download_finished(dest_path)
                # Do NOT emit standard download complete signals here
                # The special handler will manage the download sequence
            else:
                # For regular files, emit standard completion signals
                self.emit_signal(
                    SignalCode.DOWNLOAD_COMPLETE, {"file_name": dest_path}
                )
                self.file_download_finished.emit()

        except Exception as e:
            self.parent.update_download_log(
                {"message": f"Failed to download {label or url}: {e}"}
            )
            # Even on error, decrement the counter so we don't get stuck
            self.total_models_in_current_step = max(
                0, self.total_models_in_current_step - 1
            )

    def download_openvoice_and_unidic(self):
        """
        Download unidic and OpenVoice checkpoints, using direct URL download for these files.
        Extraction and cleanup will be handled after all downloads are finished.
        If the unidic and openvoice folders already exist and are non-empty, skip download and extraction.
        For unidic, extract to the unidic package directory as per `python -m unidic download`.
        """
        # Set state flag to track this step has been attempted
        self._openvoice_unidic_download_attempted = True

        base_path = self.path_settings.base_path
        self._openvoice_dir = os.path.expanduser(
            os.path.join(base_path, "text", "models", "tts", "openvoice")
        )

        # Find unidic package path
        unidic_spec = importlib.util.find_spec("unidic")
        if unidic_spec is not None and unidic_spec.submodule_search_locations:
            self._unidic_dir = os.path.join(
                unidic_spec.submodule_search_locations[0]
            )
        else:
            self._unidic_dir = None

        # Skip if both folders exist and are non-empty
        openvoice_exists = os.path.isdir(self._openvoice_dir) and os.listdir(
            self._openvoice_dir
        )
        unidic_exists = (
            self._unidic_dir
            and os.path.isdir(self._unidic_dir)
            and os.listdir(self._unidic_dir)
        )

        if unidic_exists and openvoice_exists:
            self.parent.update_download_log(
                {
                    "message": "Unidic and OpenVoice already present, skipping download."
                }
            )
            # Signal completion through normal flow rather than directly calling finalize_installation
            self._openvoice_unidic_complete = True
            self.total_models_in_current_step = 0
            self.emit_signal(SignalCode.DOWNLOAD_COMPLETE, {})
            return

        if self._unidic_dir:
            os.makedirs(self._unidic_dir, exist_ok=True)
        os.makedirs(self._openvoice_dir, exist_ok=True)

        # Download unidic zip if needed
        if not unidic_exists and self._unidic_dir:
            self.parent.on_set_downloading_status_label(
                {"label": "Downloading unidic dictionary..."}
            )
            self._unidic_zip_path = os.path.join(
                self._unidic_dir, "unidic-3.1.0.zip"
            )
            unidic_url = "https://cotonoha-dic.s3-ap-northeast-1.amazonaws.com/unidic-3.1.0.zip"
            self.total_models_in_current_step += 1  # Track unidic zip
            self._download_file_with_progress(
                unidic_url, self._unidic_zip_path, label="unidic-3.1.0.zip"
            )
        else:
            self._unidic_zip_path = None
            self.parent.update_download_log(
                {"message": "Unidic already present, skipping download."}
            )

        # OpenVoice download if needed
        if not openvoice_exists:
            # Initialize OpenVoice tracking variables
            self._openvoice_zip_urls = [
                "https://myshell-public-repo-host.s3.amazonaws.com/openvoice/checkpoints_1226.zip",
                "https://myshell-public-repo-host.s3.amazonaws.com/openvoice/checkpoints_v2_0417.zip",
            ]
            self._openvoice_zip_urls_completed = []
            self._openvoice_zip_paths = []

            self.parent.on_set_downloading_status_label(
                {"label": "Downloading OpenVoice checkpoints..."}
            )

            # Log the download attempt
            self.parent.update_download_log(
                {
                    "message": f"Starting download of OpenVoice zip files to {self._openvoice_dir}"
                }
            )

            # Start with the first zip file - rest will be downloaded sequentially
            first_url = self._openvoice_zip_urls[0]
            zip_name = os.path.basename(first_url)
            zip_path = os.path.join(self._openvoice_dir, zip_name)

            # Track this zip file download
            self.total_models_in_current_step += 1

            self.parent.update_download_log(
                {"message": f"Starting download of {zip_name} to {zip_path}"}
            )

            # Download the first zip file - completion handler will trigger the next one
            self._download_file_with_progress(
                first_url, zip_path, label=zip_name
            )
        else:
            self.parent.update_download_log(
                {"message": "OpenVoice already present, skipping download."}
            )

    def _process_next_openvoice_zip(self):
        """Process the next OpenVoice zip download in the queue"""
        if (
            not hasattr(self, "_openvoice_pending_urls")
            or not self._openvoice_pending_urls
        ):
            # All downloads have been started
            self.parent.update_download_log(
                {"message": "All OpenVoice zip downloads have been initiated"}
            )
            return

        # Get the next URL to process
        url = self._openvoice_pending_urls.pop(0)
        zip_name = os.path.basename(url)
        zip_path = os.path.join(self._openvoice_dir, zip_name)

        # Add the path to the tracking list
        self._openvoice_zip_paths.append(zip_path)
        self.total_models_in_current_step += 1  # Track each openvoice zip

        # Log the specific file being downloaded
        self.parent.update_download_log(
            {"message": f"Starting download of {zip_name} to {zip_path}"}
        )

        # Download the file - the completion will be handled through signals
        self._download_file_with_progress(url, zip_path, label=zip_name)

    def extract_openvoice_and_unidic(self):
        """
        Extract and clean up unidic and OpenVoice zips after all downloads are complete.
        For unidic, extract to the unidic package directory as per `python -m unidic download`.
        """
        # Set state flag early to prevent multiple calls
        self._openvoice_unidic_extraction_complete = True

        self.parent.update_download_log(
            {"message": "Starting extraction of downloaded files..."}
        )

        # Extract unidic
        if (
            hasattr(self, "_unidic_zip_path")
            and self._unidic_zip_path
            and self._unidic_dir
            and os.path.exists(self._unidic_zip_path)
        ):
            try:
                self.parent.on_set_downloading_status_label(
                    {"label": f"Unzipping unidic to {self._unidic_dir}..."}
                )
                self.parent.update_download_log(
                    {
                        "message": f"Extracting unidic zip from {self._unidic_zip_path}"
                    }
                )
                with zipfile.ZipFile(self._unidic_zip_path, "r") as zip_ref:
                    zip_ref.extractall(self._unidic_dir)
                os.remove(self._unidic_zip_path)
                self.parent.update_download_log(
                    {
                        "message": f"Unzipped and removed unidic-3.1.0.zip to {self._unidic_dir}"
                    }
                )
            except Exception as e:
                self.parent.update_download_log(
                    {"message": f"Failed to unzip unidic: {str(e)}"}
                )
        else:
            self.parent.update_download_log(
                {"message": "No unidic zip file to extract or file not found"}
            )

        # Extract OpenVoice - count files for more accurate progress reporting
        openvoice_extracted = False
        extraction_count = 0
        total_to_extract = 0

        if hasattr(self, "_openvoice_zip_paths"):
            # Count total files to extract first
            for zip_path in self._openvoice_zip_paths:
                if os.path.exists(zip_path):
                    total_to_extract += 1

            # Now extract each zip file
            for zip_path in self._openvoice_zip_paths:
                if not os.path.exists(zip_path):
                    self.parent.update_download_log(
                        {
                            "message": f"OpenVoice zip file not found at {zip_path}"
                        }
                    )
                    continue

                zip_name = os.path.basename(zip_path)
                try:
                    extraction_count += 1
                    progress_pct = (
                        int((extraction_count / total_to_extract) * 100)
                        if total_to_extract > 0
                        else 0
                    )

                    self.parent.on_set_downloading_status_label(
                        {
                            "label": f"Unzipping {zip_name}... ({extraction_count}/{total_to_extract})"
                        }
                    )
                    self.parent.update_download_log(
                        {
                            "message": f"Extracting OpenVoice zip from {zip_path} ({extraction_count}/{total_to_extract})"
                        }
                    )

                    # Update progress bar during extraction
                    if hasattr(self.parent, "ui") and hasattr(
                        self.parent.ui, "status_bar"
                    ):
                        self.parent.ui.status_bar.setValue(progress_pct)

                    with zipfile.ZipFile(zip_path, "r") as zip_ref:
                        zip_ref.extractall(self._openvoice_dir)

                    os.remove(zip_path)
                    openvoice_extracted = True
                    self.parent.update_download_log(
                        {
                            "message": f"Unzipped and removed {zip_name} ({extraction_count}/{total_to_extract})"
                        }
                    )
                except Exception as e:
                    self.parent.update_download_log(
                        {"message": f"Failed to unzip {zip_name}: {str(e)}"}
                    )
        else:
            self.parent.update_download_log(
                {"message": "No OpenVoice zip files to extract"}
            )

        # Final status message based on extraction success
        if openvoice_extracted:
            self.parent.on_set_downloading_status_label(
                {"label": "OpenVoice and unidic setup complete"}
            )

            # Explicitly emit a download complete signal to ensure proper step progression
            self.emit_signal(
                SignalCode.DOWNLOAD_COMPLETE,
                {"file_name": "openvoice_extraction_complete"},
            )
            self.file_download_finished.emit()
        else:
            self.parent.on_set_downloading_status_label(
                {
                    "label": "OpenVoice setup incomplete - some files may be missing"
                }
            )

        # The download_finished method will handle step progression based on total_models_in_current_step

    def verify_openvoice_downloads(self):
        """
        Verify that OpenVoice zip files exist and extract them if needed.
        This is a double-check in case the automatic extraction didn't work.
        """
        if not hasattr(self, "_openvoice_dir"):
            self.parent.update_download_log(
                {
                    "message": "OpenVoice directory not initialized, skipping verification"
                }
            )
            return

        # Check for the expected zip files that might still need extraction
        expected_files = ["checkpoints_1226.zip", "checkpoints_v2_0417.zip"]

        # Also verify the existence of key checkpoint files that should be extracted
        extracted_key_files = [
            "hubert_base.pt",  # From first zip
            "decoder.pth",  # From second zip
        ]

        # Check for unextracted zip files
        found_zips = []
        for filename in expected_files:
            path = os.path.join(self._openvoice_dir, filename)
            if os.path.exists(path):
                found_zips.append(path)
                self.parent.update_download_log(
                    {"message": f"Found unextracted file: {path}"}
                )

        # Check if extraction was successful
        missing_key_files = []
        for key_file in extracted_key_files:
            # Check both direct path and possible subdirectories for the files
            if not any(
                os.path.exists(os.path.join(dirpath, key_file))
                for dirpath, _, _ in os.walk(self._openvoice_dir)
            ):
                missing_key_files.append(key_file)

        if missing_key_files:
            self.parent.update_download_log(
                {
                    "message": f"Missing expected OpenVoice files after extraction: {', '.join(missing_key_files)}"
                }
            )

        # Extract any found zip files
        if found_zips:
            self.parent.update_download_log(
                {
                    "message": f"Performing backup extraction of {len(found_zips)} OpenVoice zip files..."
                }
            )

            for zip_path in found_zips:
                zip_name = os.path.basename(zip_path)
                try:
                    self.parent.on_set_downloading_status_label(
                        {"label": f"Manually unzipping {zip_name}..."}
                    )
                    with zipfile.ZipFile(zip_path, "r") as zip_ref:
                        zip_ref.extractall(self._openvoice_dir)
                    os.remove(zip_path)
                    self.parent.update_download_log(
                        {
                            "message": f"Successfully unzipped and removed {zip_name} in verification step"
                        }
                    )
                except Exception as e:
                    self.parent.update_download_log(
                        {
                            "message": f"Backup extraction failed for {zip_name}: {str(e)}"
                        }
                    )
        elif missing_key_files:
            # Missing key files but no zip files to extract
            self.parent.update_download_log(
                {
                    "message": "Warning: Some OpenVoice files appear to be missing, but no zip files found to extract"
                }
            )
        else:
            self.parent.update_download_log(
                {"message": "OpenVoice installation verification passed"}
            )

    def handle_openvoice_zip_download_finished(self, file_path):
        """
        Called when an OpenVoice zip file download is complete.
        Determines if we need to download the next one or proceed to extraction.
        """
        # Initialize OpenVoice tracking variables if not already done
        if not hasattr(self, "_openvoice_zip_urls"):
            self._openvoice_zip_urls = [
                "https://myshell-public-repo-host.s3.amazonaws.com/openvoice/checkpoints_1226.zip",
                "https://myshell-public-repo-host.s3.amazonaws.com/openvoice/checkpoints_v2_0417.zip",
            ]
            self._openvoice_zip_urls_completed = []
            self._openvoice_zip_paths = []

        # Mark this URL as completed
        file_name = os.path.basename(file_path)
        for url in self._openvoice_zip_urls[
            :
        ]:  # Use a copy for iteration during modification
            if file_name in url:
                self._openvoice_zip_urls.remove(url)
                self._openvoice_zip_urls_completed.append(url)

        # Add to tracked zip paths if not already present
        if not hasattr(self, "_openvoice_zip_paths"):
            self._openvoice_zip_paths = []

        if file_path not in self._openvoice_zip_paths:
            self._openvoice_zip_paths.append(file_path)

        self.parent.update_download_log(
            {
                "message": f"Completed download of {file_name}, {len(self._openvoice_zip_urls)} OpenVoice files remaining"
            }
        )

        # Check if we have more files to download
        if self._openvoice_zip_urls:
            # Start downloading the next file
            next_url = self._openvoice_zip_urls[0]
            next_file_name = os.path.basename(next_url)
            next_file_path = os.path.join(self._openvoice_dir, next_file_name)

            self.parent.update_download_log(
                {
                    "message": f"Starting next OpenVoice zip download: {next_file_name}"
                }
            )

            # Increment the counter since we're starting another download
            self.total_models_in_current_step += 1

            # Download the next file (this will be handled by this same handler when complete)
            self._download_file_with_progress(
                next_url, next_file_path, label=next_file_name
            )
        else:
            # All downloads are complete, extract files after a brief delay
            self.parent.update_download_log(
                {
                    "message": "All OpenVoice zip downloads complete, starting extraction..."
                }
            )

            # Schedule extraction with a brief delay to avoid race conditions
            # This ensures all signal handlers complete before we begin extraction
            QTimer.singleShot(100, self.extract_openvoice_and_unidic)

    @Slot()
    def download_finished(self, data):
        self.total_models_in_current_step = max(
            0, self.total_models_in_current_step - 1
        )

        if self.total_models_in_current_step <= 0:
            if self.current_step == 8:
                # Check for state flags to track progress through step 8
                if not hasattr(self, "_openvoice_unidic_download_attempted"):
                    # First phase: OpenVoice models are done, now download zip files
                    self.download_openvoice_and_unidic()
                    return
                elif not hasattr(
                    self, "_openvoice_unidic_extraction_complete"
                ):
                    # Check if we have OpenVoice zip files that need extraction
                    has_unidic = (
                        hasattr(self, "_unidic_zip_path")
                        and self._unidic_zip_path
                        and os.path.exists(self._unidic_zip_path)
                    )

                    has_openvoice = False
                    if hasattr(self, "_openvoice_zip_paths"):
                        for path in self._openvoice_zip_paths:
                            if os.path.exists(path):
                                has_openvoice = True
                                break

                    # Attempt extraction if we have any zip files
                    if has_unidic or has_openvoice:
                        self.extract_openvoice_and_unidic()
                        return
                    else:
                        # No files to extract, mark step as complete
                        self._openvoice_unidic_extraction_complete = True

            # Move to next step only if we get here
            self.set_page()

    @Slot()
    def path_set(self):
        self.set_page()

    def run(self):
        # Start installation process - we're already in the install page so agreements should be checked
        self.current_step = -1
        self.set_page()

    def set_page(self):
        if self.current_step == -1:
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
        elif self.current_step == 1:
            self.parent.on_set_downloading_status_label(
                {"label": f"Downloading Controlnet"}
            )
            self.current_step = 2
            self.download_controlnet()
        elif self.current_step == 2:
            self.current_step = 3
            self.download_controlnet_processors()
        elif self.current_step == 3:
            self.parent.on_set_downloading_status_label(
                {"label": f"Downloading LLM"}
            )
            self.current_step = 4
            self.download_llms()
        elif self.current_step == 4:
            self.parent.on_set_downloading_status_label(
                {"label": f"Downloading Text-to-Speech"}
            )
            self.current_step = 5
            self.download_tts()
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
            # Set step before downloading to ensure processing in download_finished
            self.current_step = 8
            self.download_openvoice()
            # Only download unidic/openvoice zips after OpenVoice models are completed
            # download_openvoice_and_unidic will be called automatically when OpenVoice models finish
        elif self.current_step == 8:
            # Only called when set_page() runs after step 8 completes
            self.finalize_installation()

    def finalize_installation(self, *_args):
        # Check if installation is already finalized to prevent multiple calls
        if (
            hasattr(self, "_installation_finalized")
            and self._installation_finalized
        ):
            return

        self._installation_finalized = True

        self.parent.update_download_log(
            {"message": "Beginning final installation steps..."}
        )

        # Perform a verification check on OpenVoice files before finalizing
        # This ensures files are extracted even if the normal process didn't work
        try:
            self.parent.update_download_log(
                {"message": "Verifying OpenVoice files..."}
            )
            self.verify_openvoice_downloads()
        except Exception as e:
            self.parent.update_download_log(
                {"message": f"Error during OpenVoice verification: {str(e)}"}
            )

        # Download NLTK data with proper error handling
        self.parent.update_download_log(
            {"message": "Downloading NLTK data..."}
        )
        nltk_data = ["averaged_perceptron_tagger_eng", "punkt", "punkt_tab"]

        if nltk is None:
            self.logger.error(
                "NLTK not available, skipping NLTK data download"
            )
            return

        try:
            # Use a maximum recursion limiter to prevent potential recursion errors
            original_limit = sys.getrecursionlimit()
            sys.setrecursionlimit(1500)  # Set a reasonable limit

            for data_name in nltk_data:
                try:
                    nltk.download(data_name, quiet=True)
                    self.parent.update_download_log(
                        {"message": f"Downloaded NLTK {data_name}"}
                    )
                except Exception as e:
                    self.parent.update_download_log(
                        {
                            "message": f"Failed to download NLTK {data_name}: {e}"
                        }
                    )

            # Reset recursion limit
            sys.setrecursionlimit(original_limit)

        except Exception as e:
            self.parent.update_download_log(
                {"message": f"Failed to download NLTK data: {e}"}
            )

        self.parent.on_set_downloading_status_label(
            {"label": "Installation complete."}
        )

        # Log final completion
        self.parent.update_download_log(
            {"message": "All installation steps completed successfully"}
        )

        # Make sure we complete all downloads in the counter
        if self.parent.total_files != self.parent.total_files_downloaded:
            self.parent.total_files_downloaded = self.parent.total_files

        # Force progress bar to show completion
        self.parent.update_progress_bar(final=True)


class InstallPage(BaseWizard):
    class_name_ = Ui_install_page

    def __init__(
        self,
        parent,
        stablediffusion_models: List[Dict[str, str]],
        models_enabled: List[str],
    ):
        super(InstallPage, self).__init__(parent)
        self.total_files_downloaded = 0
        self.total_files = 0
        self.stablediffusion_models = stablediffusion_models
        self.models_enabled = models_enabled
        self.steps_completed = 0

        # reset the progress bar
        self.ui.progress_bar.setValue(0)
        self.ui.progress_bar.setMaximum(100)

        # Disable the Next button when starting downloads
        if hasattr(parent, "button") and parent.button(
            QWizard.WizardButton.NextButton
        ):
            parent.button(QWizard.WizardButton.BackButton).setEnabled(False)
            parent.button(QWizard.WizardButton.NextButton).setEnabled(False)

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

        if self.models_enabled["openvoice_model"]:
            for k, v in OPENVOICE_FILES.items():
                self.total_steps += len(v["files"])

        # Register update_progress_bar to receive download_complete signals with file data
        self.register(SignalCode.DOWNLOAD_COMPLETE, self.on_download_complete)
        self.register(SignalCode.DOWNLOAD_PROGRESS, self.download_progress)
        self.register(SignalCode.UPDATE_DOWNLOAD_LOG, self.update_download_log)
        self.register(
            SignalCode.CLEAR_DOWNLOAD_STATUS_BAR, self.clear_status_bar
        )
        self.register(
            SignalCode.SET_DOWNLOAD_STATUS_LABEL,
            self.on_set_downloading_status_label,
        )

        # Create and configure worker thread
        self.thread = QThread()
        self.worker = InstallWorker(
            self, models_enabled=self.models_enabled, initialize_gui=False
        )
        self.worker.moveToThread(self.thread)

        # Connect worker signals
        self.worker.file_download_finished.connect(self.file_download_finished)
        self.worker.progress_updated.connect(self.file_progress_updated)

        # Connect thread signals
        self.thread.started.connect(self.worker.run)

        # Calculate total files and start immediately
        self.calculate_total_files()
        self.thread.start()

    def calculate_total_files(self):
        if self.models_enabled["stable_diffusion"]:
            models = model_bootstrap_data
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
                    files = SD_FILE_BOOTSTRAP_DATA[model["version"]][
                        action_key
                    ]
                    self.total_files += len(files)
                except KeyError:
                    continue

            for controlnet_model in controlnet_bootstrap_data:
                if not self.models_enabled.get(controlnet_model["name"], True):
                    continue
                files = SD_FILE_BOOTSTRAP_DATA[controlnet_model["version"]][
                    "controlnet"
                ]
                self.total_files += len(files)

            self.total_files += len(controlnet_processor_files)

        if self.models_enabled["mistral"]:
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
                    files = LLM_FILE_BOOTSTRAP_DATA[model["path"]]["files"]
                    self.total_files += len(files)

        if self.models_enabled["whisper"]:
            for k, v in WHISPER_FILES.items():
                self.total_files += len(v)

        if self.models_enabled["speecht5"]:
            for k, v in SPEECH_T5_FILES.items():
                self.total_files += len(v)

        if self.models_enabled["openvoice_model"]:
            for k, v in OPENVOICE_FILES.items():
                self.total_files += len(v["files"])

    def start(self):
        """Start the installation process and ensure Next button is disabled"""
        # Make sure Next button is disabled when downloads start
        if hasattr(self.parent, "button") and self.parent.button(
            QWizard.WizardButton.NextButton
        ):
            self.parent.button(QWizard.WizardButton.BackButton).setEnabled(
                False
            )
            self.parent.button(QWizard.WizardButton.NextButton).setEnabled(
                False
            )

        # Connect signals and start the thread
        self.calculate_total_files()
        self.worker.file_download_finished.connect(self.file_download_finished)
        self.worker.progress_updated.connect(self.file_progress_updated)
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    def file_download_finished(self):
        """Handler for when a file download completes"""

    def file_progress_updated(self, current, total):
        """Handler for download progress updates"""
        self.download_progress({"current": current, "total": total})

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

    def update_progress_bar(self, final: bool = False, data: dict = None):
        """Update the progress bar and manage Next button state"""
        # Only increment counter if this is a file completion event
        # or final progress update
        if self.total_files == 0 and not final:
            return

        # If data is provided and contains file_name, this is a download completion event
        if data and "file_name" in data:
            self.total_files_downloaded += 1
        # If this is the final update, don't increment counter
        elif not final and not data:
            # This is a generic update_progress_bar call without specific file completion
            # Only increment if specifically requested (legacy handling)
            self.total_files_downloaded += 1

        # Never exceed total files
        if self.total_files_downloaded > self.total_files:
            self.total_files_downloaded = self.total_files

        if self.total_files == self.total_files_downloaded:
            self.ui.progress_bar.setValue(100)

            # Add a slight delay before enabling the Next button
            # to ensure all processing is complete
            QTimer.singleShot(500, self._enable_next_button)
        else:
            val = 0
            if self.total_files > 0:
                val = (self.total_files_downloaded / self.total_files) * 100
            self.ui.progress_bar.setValue(val)

    def _enable_next_button(self):
        """Enable the Next button when installation is complete"""
        if hasattr(self.parent, "button") and self.parent.button(
            QWizard.WizardButton.NextButton
        ):
            self.parent.button(QWizard.WizardButton.NextButton).setEnabled(
                True
            )

    def set_status(self, message: str):
        # set the text of a QProgressBar
        self.ui.status_bar.setFormat(message)

    def update_download_log(self, data: dict):
        self.ui.log.appendPlainText(data["message"] + "\n")

    def clear_status_bar(self):
        self.ui.status.setText("")
        self.ui.status_bar.setValue(0)

    def on_download_complete(self, data: dict = None):
        """
        Handles download complete signals with proper data tracking.
        This ensures the progress bar is updated correctly and prevents double-counting.
        """
        # Update the progress bar with the file data
        self.update_progress_bar(data=data)
