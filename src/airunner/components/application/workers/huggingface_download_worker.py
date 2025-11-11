"""Worker for HuggingFace model downloads using Python threading."""

import os
import threading
from pathlib import Path
import requests

from airunner.components.application.workers.base_download_worker import (
    BaseDownloadWorker,
)
from airunner.enums import SignalCode
from airunner.components.llm.utils.model_downloader import (
    HuggingFaceDownloader,
)
from airunner.utils.settings.get_qsettings import get_qsettings
from airunner.settings import MODELS_DIR
from airunner.components.data.bootstrap.unified_model_files import (
    get_required_files_for_model,
)


class HuggingFaceDownloadWorker(BaseDownloadWorker):
    """Worker for downloading HuggingFace models with parallel file downloading."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.downloader = HuggingFaceDownloader()

    @property
    def _complete_signal(self) -> SignalCode:
        """Signal to emit on successful download completion."""
        return SignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE

    @property
    def _failed_signal(self) -> SignalCode:
        """Signal to emit on download failure."""
        return SignalCode.HUGGINGFACE_DOWNLOAD_FAILED

    def _download_model(
        self,
        repo_id: str,
        model_type: str,
        output_dir: str,
        version: str = None,
        pipeline_action: str = "txt2img",
        missing_files: list = None,
    ):
        """Download model files from HuggingFace.

        Args:
            repo_id: HuggingFace repository ID (e.g., "black-forest-labs/FLUX.1-dev")
            model_type: Type of model (llm, flux, etc.)
            output_dir: Directory to save the model
            version: Version name for bootstrap data lookup (e.g., "SDXL 1.0", "Flux.1 S")
            pipeline_action: Pipeline action (txt2img, inpaint, etc.)
            missing_files: Specific list of files to download (if provided, only these files will be downloaded)

        """
        self.logger.info(
            f"_download_model called with repo_id={repo_id}, model_type={model_type}, "
            f"output_dir={output_dir}, version={version}, pipeline_action={pipeline_action}, "
            f"missing_files={missing_files}"
        )

        settings = get_qsettings()
        api_key = settings.value("huggingface/api_key", "")

        if not output_dir:
            output_dir = os.path.join(MODELS_DIR, "text/models/llm/causallm")

        # For art models, don't create a subdirectory - use output_dir directly
        # since it already points to the correct location (e.g., the GGUF file's directory)
        if model_type in ("flux", "art"):
            model_path = Path(output_dir)
            self.logger.info(
                f"Using output_dir directly for art model: {model_path}"
            )
        else:
            model_name = repo_id.split("/")[-1]
            model_path = Path(output_dir) / model_name
            self.logger.info(
                f"Creating subdirectory for LLM model: {model_path}"
            )

        # Initialize download state
        self.is_cancelled = False
        self._completed_files.clear()
        self._failed_files.clear()
        self._file_progress.clear()
        self._file_sizes.clear()
        self._file_threads.clear()
        self._total_downloaded = 0
        self._total_size = 0

        temp_dir = model_path / ".downloading"
        temp_dir.mkdir(parents=True, exist_ok=True)

        self._model_path = model_path
        self._temp_dir = temp_dir

        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {"message": f"Starting download: {repo_id}"},
        )

        # Get list of files from HuggingFace API
        try:
            all_files = self.downloader.get_model_files(repo_id)
        except Exception as e:
            self.emit_signal(self._failed_signal, {"error": str(e)})
            return

        # Filter files to download
        # If specific missing_files list is provided, use ONLY those files
        # Otherwise, use the comprehensive bootstrap data
        is_art_model = model_type in ("flux", "art")

        if missing_files:
            # Use the explicitly provided missing files list
            # This bypasses all skip logic (e.g., GGUF transformer skip)
            self.logger.info(
                f"Using explicitly provided missing_files list ({len(missing_files)} files)"
            )
            required_files = missing_files
        elif is_art_model:
            # Use the version parameter if provided, otherwise try FLUX versions
            version_names = []
            if version:
                version_names.append(version)
                self.logger.info(
                    f"Using provided version for bootstrap data: {version}"
                )
            else:
                version_names = ["Flux.1 S", "FLUX"]
                self.logger.warning(
                    f"No version provided, trying fallback versions: {version_names}"
                )

            required_files = None
            for version_name in version_names:
                self.logger.info(
                    f"Trying to get required files for version: {version_name}, pipeline_action: {pipeline_action}"
                )
                required_files = get_required_files_for_model(
                    "art", version_name, version_name, pipeline_action
                )
                if required_files:
                    self.logger.info(
                        f"Found {len(required_files)} required files for {version_name}: {required_files[:5]}..."
                    )
                    break
                else:
                    self.logger.warning(
                        f"No required files found for {version_name} with pipeline_action {pipeline_action}"
                    )

            if required_files is None or len(required_files) == 0:
                self.logger.error(
                    f"No bootstrap data found for {model_type} (version={version})! Cannot determine required files."
                )
                self.emit_signal(
                    self._failed_signal,
                    {
                        "error": f"No bootstrap data found for {model_type} (version={version})"
                    },
                )
                return
        else:
            # For LLM models, use the minimal required files from downloader
            required_files = self.downloader.REQUIRED_FILES.get(
                model_type, self.downloader.REQUIRED_FILES["llm"]
            )

        files_to_download = []

        for file_info in all_files:
            filename = file_info.get("path", "")

            # Skip directories
            if file_info.get("type") == "directory":
                continue

            # Skip if already exists
            final_path = model_path / filename
            if final_path.exists():
                continue

            # For art models with required_files list, check if file is in the list
            if is_art_model and required_files:
                # Check if filename matches any required file
                if filename in required_files:
                    # Skip transformer weights ONLY if we got files from bootstrap data
                    # (not from explicit missing_files list) AND if GGUF exists
                    # When missing_files is explicitly provided, download ALL requested files
                    if (
                        not missing_files  # Only skip if using bootstrap data
                        and "transformer/diffusion_pytorch_model" in filename
                        and filename.endswith(".safetensors")
                    ):
                        self.logger.info(
                            f"Skipping transformer weights (using GGUF): {filename}"
                        )
                        continue

                    files_to_download.append(
                        {
                            "filename": filename,
                            "size": file_info.get("size", 0),
                        }
                    )
                else:
                    # File not in required_files, skip it for art models
                    pass
                continue

            # Include required files (config, tokenizer files) for LLM models
            if filename in required_files:
                files_to_download.append(
                    {"filename": filename, "size": file_info.get("size", 0)}
                )
                continue

            # For art models without specific required_files, skip everything
            if is_art_model:
                continue

            # For LLM models: Include model shards and config files
            # EXCLUDE consolidated.safetensors - we need individual shards for gradual loading
            if filename == "consolidated.safetensors":
                continue

            # Include all config/tokenizer/model files (.json, .txt, .model, .safetensors)
            if filename.endswith((".safetensors", ".json", ".txt", ".model")):
                files_to_download.append(
                    {"filename": filename, "size": file_info.get("size", 0)}
                )

        if not files_to_download:
            self.emit_signal(
                SignalCode.UPDATE_DOWNLOAD_LOG,
                {"message": "All files already downloaded!"},
            )
            self.emit_signal(
                self._complete_signal,
                {"model_path": str(model_path)},
            )
            return

        self._total_size = sum(f["size"] for f in files_to_download)
        total_gb = self._total_size / (1024**3)

        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {
                "message": f"Downloading {len(files_to_download)} files ({total_gb:.2f} GB) in parallel"
            },
        )

        # Start download threads
        for file_info in files_to_download:
            if self.is_cancelled:
                return

            filename = file_info["filename"]
            file_size = file_info["size"]

            self._file_sizes[filename] = file_size
            self._file_progress[filename] = 0

            self.emit_signal(
                SignalCode.UPDATE_DOWNLOAD_LOG,
                {"message": f"Starting download thread for {filename}..."},
            )

            thread = threading.Thread(
                target=self._download_file,
                args=(
                    repo_id,
                    filename,
                    file_size,
                    self._temp_dir,
                    model_path,
                    api_key,
                ),
                daemon=True,
            )
            self._file_threads[filename] = thread
            thread.start()

        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {
                "message": f"Started {len(files_to_download)} download threads, waiting for completion..."
            },
        )

        # Wait for completion
        if not self._wait_for_completion(len(files_to_download)):
            return

        self._cleanup_temp_files()
        self.emit_signal(
            self._complete_signal,
            {"model_path": str(model_path)},
        )

    def _download_file(
        self,
        repo_id: str,
        filename: str,
        file_size: int,
        temp_dir: Path,
        model_path: Path,
        api_key: str,
    ):
        """Download a single file from HuggingFace (runs in Python thread).

        Args:
            repo_id: HuggingFace repository ID
            filename: Name of file to download
            file_size: Expected size in bytes
            temp_dir: Temporary download directory
            model_path: Final model directory
            api_key: HuggingFace API key (optional)
        """
        temp_path = temp_dir / filename
        final_path = model_path / filename

        # Create parent directories for files in subdirectories
        temp_path.parent.mkdir(parents=True, exist_ok=True)

        url = f"https://huggingface.co/{repo_id}/resolve/main/{filename}"
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            with requests.get(
                url, headers=headers, stream=True, timeout=30
            ) as response:
                response.raise_for_status()

                content_length = response.headers.get("content-length")
                if content_length:
                    file_size = int(content_length)
                    with self._lock:
                        self._file_sizes[filename] = file_size

                downloaded = 0
                with open(temp_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if self.is_cancelled:
                            f.close()
                            if temp_path.exists():
                                temp_path.unlink()
                            return

                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

                            if downloaded % (1024 * 1024) < 8192:
                                self._update_file_progress(
                                    filename, downloaded, file_size
                                )

                self._update_file_progress(filename, downloaded, file_size)

                final_path.parent.mkdir(parents=True, exist_ok=True)
                if final_path.exists():
                    final_path.unlink()
                temp_path.rename(final_path)

                self._mark_file_complete(filename)

        except Exception as e:
            self.logger.error(f"Failed to download {filename}: {e}")
            self._mark_file_failed(filename)

            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
