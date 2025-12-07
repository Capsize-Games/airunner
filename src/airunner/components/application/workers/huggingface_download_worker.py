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
from airunner.components.llm.utils.ministral3_config_patcher import (
    patch_ministral3_config,
    is_ministral3_model,
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
        self._current_model_type = None  # Set by _download_model for completion signals
        self._current_pipeline_action = None  # Set by _download_model for completion signals

    @property
    def _complete_signal(self) -> SignalCode:
        """Signal to emit on successful download completion."""
        return SignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE

    @property
    def _failed_signal(self) -> SignalCode:
        """Signal to emit on download failure."""
        return SignalCode.HUGGINGFACE_DOWNLOAD_FAILED

    def _apply_post_download_patches(self, model_path: Path) -> None:
        """Apply post-download patches for models requiring config fixes.

        Some models like Ministral3 have config files that need patching
        for transformers compatibility. This method applies necessary patches
        after download completes.

        Args:
            model_path: Path to the downloaded model directory.
        """
        try:
            if is_ministral3_model(model_path):
                self.logger.info(f"Applying Ministral3 config patches to {model_path}")
                if patch_ministral3_config(model_path):
                    self.emit_signal(
                        SignalCode.UPDATE_DOWNLOAD_LOG,
                        {"message": "Applied Ministral3 config patches for transformers compatibility."},
                    )
                else:
                    self.logger.debug(f"Ministral3 configs already patched at {model_path}")
        except Exception as e:
            self.logger.warning(f"Failed to apply post-download patches: {e}")

    def _download_model(
        self,
        repo_id: str = None,
        model_type: str = None,
        output_dir: str = None,
        version: str = None,
        pipeline_action: str = "txt2img",
        missing_files: list = None,
        gguf_filename: str = None,
        zip_url: str = None,
    ):
        """Download model files from HuggingFace or direct URL.

        Args:
            repo_id: HuggingFace repository ID (e.g., "black-forest-labs/FLUX.1-dev")
            model_type: Type of model (llm, flux, gguf, openvoice_zip, etc.)
            output_dir: Directory to save the model
            version: Version name for bootstrap data lookup (e.g., "SDXL 1.0", "Flux.1 S")
            pipeline_action: Pipeline action (txt2img, inpaint, etc.)
            missing_files: Specific list of files to download (if provided, only these files will be downloaded)
            gguf_filename: For GGUF downloads, the specific .gguf file to download
            zip_url: For ZIP downloads, the direct URL to download

        """
        # Store model_type and pipeline_action immediately for use in completion signals
        self._current_model_type = model_type
        self._current_pipeline_action = pipeline_action
        
        self.logger.info(
            f"_download_model called with repo_id={repo_id}, model_type={model_type}, "
            f"output_dir={output_dir}, version={version}, pipeline_action={pipeline_action}, "
            f"missing_files={missing_files}, gguf_filename={gguf_filename}, zip_url={zip_url}"
        )

        # Handle ZIP file downloads (OpenVoice checkpoints)
        if model_type == "openvoice_zip" and zip_url:
            self._download_and_extract_zip(zip_url, output_dir)
            return

        # Handle GGUF downloads specially - just download the single file
        if model_type == "gguf" and gguf_filename:
            self._download_gguf_model(repo_id, output_dir, gguf_filename)
            return

        settings = get_qsettings()
        api_key = settings.value("huggingface/api_key", "")

        if not output_dir:
            output_dir = os.path.join(MODELS_DIR, "text/models/llm/causallm")

        # For art/stt/tts models, don't create a subdirectory - use output_dir directly
        # since it already points to the correct location
        is_stt_tts = model_type in ("stt", "tts_openvoice")
        if model_type == "art" or is_stt_tts:
            model_path = Path(output_dir)
            self.logger.info(
                f"Using output_dir directly for {model_type} model: {model_path}"
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

        # Filter files to download
        # If specific missing_files list is provided, use ONLY those files
        # Otherwise, use the comprehensive bootstrap data
        is_art_model = model_type == "art"
        is_stt_tts_model = model_type in ("stt", "tts_openvoice")
        is_llm_model = model_type in ("llm", "ministral3", "gguf")

        # For art/stt/tts models, use bootstrap data directly (no API call)
        # For LLM models, we still need API to discover model shards
        bootstrap_files = None  # Dict of {filename: expected_size} for art models, or list for stt/tts
        full_bootstrap_data = None  # Full bootstrap data for size lookups

        # First, get the full bootstrap data based on model type
        if is_art_model:
            version_names = []
            if version:
                version_names.append(version)
            else:
                version_names = ["Flux.1 S", "FLUX"]

            for version_name in version_names:
                full_bootstrap_data = get_required_files_for_model(
                    "art", version_name, version_name, pipeline_action
                )
                if full_bootstrap_data:
                    self.logger.info(
                        f"Found bootstrap data for {version_name} with {len(full_bootstrap_data)} files"
                    )
                    break
        elif is_stt_tts_model:
            # For STT/TTS models, get the list of required files from bootstrap data
            full_bootstrap_data = get_required_files_for_model(
                model_type, repo_id
            )
            if full_bootstrap_data:
                self.logger.info(
                    f"Found bootstrap data for {model_type}/{repo_id} with {len(full_bootstrap_data)} files"
                )
        elif is_llm_model:
            # For LLM models, get bootstrap data for file size validation
            full_bootstrap_data = get_required_files_for_model("llm", repo_id)
            if full_bootstrap_data:
                self.logger.info(
                    f"Found bootstrap data for llm/{repo_id} with {len(full_bootstrap_data)} files"
                )
            else:
                self.logger.warning(
                    f"No bootstrap data found for llm/{repo_id} - file sizes will be fetched from API"
                )

        if missing_files:
            # Use the explicitly provided missing files list
            # Look up expected sizes from bootstrap data
            self.logger.info(
                f"Using explicitly provided missing_files list ({len(missing_files)} files)"
            )
            bootstrap_files = {}
            for f in missing_files:
                # Get expected size from full bootstrap data if available
                expected_size = 0
                if full_bootstrap_data and isinstance(full_bootstrap_data, dict) and f in full_bootstrap_data:
                    expected_size = full_bootstrap_data[f]
                    self.logger.info(f"Missing file {f}: expected size {expected_size} (from bootstrap)")
                else:
                    self.logger.warning(f"Missing file {f}: no expected size found in bootstrap data")
                bootstrap_files[f] = expected_size
        elif is_art_model:
            bootstrap_files = full_bootstrap_data

            if bootstrap_files is None or len(bootstrap_files) == 0:
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
        elif is_stt_tts_model:
            # For STT/TTS models, bootstrap data is a list of filenames (no sizes)
            # Convert to dict with size=0 (unknown) for compatibility
            if full_bootstrap_data:
                bootstrap_files = {f: 0 for f in full_bootstrap_data}
            else:
                self.logger.error(
                    f"No bootstrap data found for {model_type}/{repo_id}! Cannot determine required files."
                )
                self.emit_signal(
                    self._failed_signal,
                    {
                        "error": f"No bootstrap data found for {model_type}/{repo_id}"
                    },
                )
                return

        # For art/stt/tts models with bootstrap data, use it directly without API call
        if (is_art_model or is_stt_tts_model) and bootstrap_files:
            files_to_download = []

            for filename, expected_size in bootstrap_files.items():
                # Check if file already exists and is complete
                final_path = model_path / filename

                if final_path.exists():
                    actual_size = final_path.stat().st_size
                    if expected_size > 0 and actual_size < expected_size:
                        # File is incomplete - needs re-download
                        self.logger.warning(
                            f"File {filename} is incomplete: {actual_size} bytes vs expected {expected_size} bytes. "
                            "Will re-download."
                        )
                        self.emit_signal(
                            SignalCode.UPDATE_DOWNLOAD_LOG,
                            {
                                "message": f"Incomplete file detected: {filename} ({actual_size / (1024**2):.1f} MB / {expected_size / (1024**2):.1f} MB). Re-downloading..."
                            },
                        )
                        # Delete incomplete file so it can be re-downloaded
                        try:
                            final_path.unlink()
                        except Exception as e:
                            self.logger.error(f"Failed to delete incomplete file {filename}: {e}")
                            continue
                    elif expected_size == 0 and actual_size < 1024:
                        # No expected size known, but file is suspiciously small (< 1KB)
                        # This likely means the download was interrupted very early
                        self.logger.warning(
                            f"File {filename} exists but is very small ({actual_size} bytes) with unknown expected size. "
                            "Assuming incomplete and re-downloading."
                        )
                        try:
                            final_path.unlink()
                        except Exception as e:
                            self.logger.error(f"Failed to delete suspicious file {filename}: {e}")
                            continue
                    else:
                        # File exists and appears complete (or we can't verify)
                        self.logger.debug(f"File {filename} exists ({actual_size} bytes), skipping")
                        continue

                # Skip transformer weights if using GGUF (only when not explicitly provided)
                if (
                    not missing_files
                    and "transformer/diffusion_pytorch_model" in filename
                    and filename.endswith(".safetensors")
                ):
                    self.logger.info(
                        f"Skipping transformer weights (using GGUF): {filename}"
                    )
                    continue

                files_to_download.append(
                    {"filename": filename, "size": expected_size}
                )

        else:
            # For LLM models, get list of files from HuggingFace API
            self.logger.info(f"Fetching file list from HuggingFace API for {repo_id}...")
            self.emit_signal(
                SignalCode.UPDATE_DOWNLOAD_LOG,
                {"message": f"Fetching file list from HuggingFace..."},
            )
            try:
                all_files = self.downloader.get_model_files(repo_id)
                self.logger.info(f"Got {len(all_files)} files from HuggingFace API")
            except Exception as e:
                self.logger.error(f"Failed to get file list: {e}")
                self.emit_signal(self._failed_signal, {"error": str(e)})
                return

            # For LLM models, use the minimal required files from downloader
            required_files = self.downloader.REQUIRED_FILES.get(
                model_type, self.downloader.REQUIRED_FILES["llm"]
            )

            files_to_download = []

            for file_info in all_files:
                filename = file_info.get("path", "")
                expected_size = file_info.get("size", 0)

                # Skip directories
                if file_info.get("type") == "directory":
                    continue

                # Check if file already exists and is complete
                final_path = model_path / filename
                if final_path.exists():
                    actual_size = final_path.stat().st_size
                    if expected_size > 0 and actual_size < expected_size:
                        # File is incomplete - needs re-download
                        self.logger.warning(
                            f"File {filename} is incomplete: {actual_size} bytes vs expected {expected_size} bytes. "
                            "Will re-download."
                        )
                        self.emit_signal(
                            SignalCode.UPDATE_DOWNLOAD_LOG,
                            {
                                "message": f"Incomplete file detected: {filename} ({actual_size / (1024**2):.1f} MB / {expected_size / (1024**2):.1f} MB). Re-downloading..."
                            },
                        )
                        # Delete incomplete file so it can be re-downloaded
                        try:
                            final_path.unlink()
                        except Exception as e:
                            self.logger.error(f"Failed to delete incomplete file {filename}: {e}")
                            continue
                    else:
                        # File exists and appears complete
                        continue

                # Include required files (config, tokenizer files) for LLM models
                if filename in required_files:
                    files_to_download.append(
                        {"filename": filename, "size": expected_size}
                    )
                    continue

                # For LLM models: Include model shards and config files
                # EXCLUDE consolidated.safetensors - we need individual shards for gradual loading
                if filename == "consolidated.safetensors":
                    continue

                # Include all config/tokenizer/model files (.json, .txt, .model, .jinja, .safetensors)
                if filename.endswith((".safetensors", ".json", ".txt", ".model", ".jinja")):
                    files_to_download.append(
                        {"filename": filename, "size": expected_size}
                    )

        if not files_to_download:
            self.emit_signal(
                SignalCode.UPDATE_DOWNLOAD_LOG,
                {"message": "All files already downloaded!"},
            )
            # Apply post-download patches even if files exist (may not be patched yet)
            self._apply_post_download_patches(model_path)
            self.emit_signal(
                self._complete_signal,
                {"model_path": str(model_path), "repo_id": repo_id, "model_type": self._current_model_type, "pipeline_action": self._current_pipeline_action},
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
        
        # Apply post-download patches (e.g., Ministral3 config fixes)
        self._apply_post_download_patches(model_path)
        
        self.emit_signal(
            self._complete_signal,
            {"model_path": str(model_path), "repo_id": repo_id, "model_type": self._current_model_type, "pipeline_action": self._current_pipeline_action},
        )

    def _download_and_extract_zip(self, zip_url: str, output_dir: str):
        """Download and extract a ZIP file with progress tracking.

        Args:
            zip_url: Direct URL to the ZIP file
            output_dir: Directory to extract to
        """
        import zipfile
        import tempfile

        filename = os.path.basename(zip_url)
        model_path = Path(output_dir)
        model_path.mkdir(parents=True, exist_ok=True)

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
            {"message": f"Starting ZIP download: {filename}"},
        )

        # Get file size
        try:
            head_response = requests.head(zip_url, allow_redirects=True, timeout=30)
            head_response.raise_for_status()
            file_size = int(head_response.headers.get("Content-Length", 0))
        except requests.RequestException as e:
            self.logger.error(f"Failed to get ZIP file size: {e}")
            file_size = 0

        self._total_size = file_size
        self._file_sizes[filename] = file_size

        size_mb = file_size / (1024 * 1024)
        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {"message": f"Downloading: {filename} ({size_mb:.1f} MB)"},
        )

        # Download the file
        temp_path = temp_dir / filename
        try:
            with requests.get(zip_url, stream=True, timeout=300) as response:
                response.raise_for_status()

                downloaded = 0
                with open(temp_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if self.is_cancelled:
                            self.emit_signal(
                                self._failed_signal,
                                {"error": "Download cancelled"},
                            )
                            return

                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

                            # Update progress every ~1MB
                            if downloaded % (1024 * 1024) < 8192:
                                self._update_file_progress(
                                    filename, downloaded, file_size
                                )

                self._update_file_progress(filename, downloaded, file_size)

            self.emit_signal(
                SignalCode.UPDATE_DOWNLOAD_LOG,
                {"message": f"Extracting {filename}..."},
            )

            # Extract the ZIP
            with zipfile.ZipFile(temp_path, "r") as zip_ref:
                zip_ref.extractall(model_path)

            # Clean up
            temp_path.unlink()
            self._cleanup_temp_files()

            self.emit_signal(
                SignalCode.UPDATE_DOWNLOAD_LOG,
                {"message": f"Successfully extracted {filename}"},
            )

            self.emit_signal(
                self._complete_signal,
                {"model_path": str(model_path), "model_type": "openvoice_zip"},
            )

        except Exception as e:
            self.logger.error(f"Failed to download/extract ZIP: {e}")
            self.emit_signal(
                self._failed_signal,
                {"error": str(e)},
            )

    def _download_gguf_model(
        self,
        repo_id: str,
        output_dir: str,
        gguf_filename: str,
    ):
        """Download a single GGUF model file from HuggingFace.

        GGUF models are pre-quantized and don't need additional processing.
        We just download the single .gguf file directly.

        Args:
            repo_id: HuggingFace repository ID (e.g., "bartowski/Ministral-3-8B-Instruct-2512-GGUF")
            output_dir: Directory to save the model
            gguf_filename: The .gguf file to download (e.g., "Ministral-3-8B-Instruct-2512-Q4_K_M.gguf")
        """
        settings = get_qsettings()
        api_key = settings.value("huggingface/api_key", "")

        model_path = Path(output_dir)
        model_path.mkdir(parents=True, exist_ok=True)

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
            {"message": f"Starting GGUF download: {repo_id}/{gguf_filename}"},
        )

        # Get file size from HuggingFace API
        url = f"https://huggingface.co/{repo_id}/resolve/main/{gguf_filename}"
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            head_response = requests.head(url, headers=headers, allow_redirects=True, timeout=30)
            head_response.raise_for_status()
            file_size = int(head_response.headers.get("Content-Length", 0))
        except requests.RequestException as e:
            self.logger.error(f"Failed to get GGUF file size: {e}")
            # Continue without size - progress will be approximate
            file_size = 0

        self._total_size = file_size
        self._file_sizes[gguf_filename] = file_size

        self.logger.info(
            f"Downloading GGUF file: {gguf_filename} ({file_size / (1024**3):.2f} GB)"
        )

        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {"message": f"Downloading: {gguf_filename} ({file_size / (1024**3):.2f} GB)"},
        )

        # Start download in thread
        thread = threading.Thread(
            target=self._download_file,
            kwargs={
                "repo_id": repo_id,
                "filename": gguf_filename,
                "file_size": file_size,
                "temp_dir": temp_dir,
                "model_path": model_path,
                "api_key": api_key,
            },
            daemon=True,
        )
        self._file_threads[gguf_filename] = thread
        thread.start()

        # Wait for completion
        if not self._wait_for_completion(1):
            return

        self._cleanup_temp_files()
        self.emit_signal(
            self._complete_signal,
            {"model_path": str(model_path), "repo_id": repo_id, "model_type": "gguf"},
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

        Supports resuming partial downloads using HTTP Range headers.

        Args:
            repo_id: HuggingFace repository ID
            filename: Name of file to download
            file_size: Expected size in bytes
            temp_dir: Temporary download directory
            model_path: Final model directory
            api_key: HuggingFace API key (optional)
        """
        self.logger.info(f"[DOWNLOAD THREAD] Starting download for {filename} from {repo_id}")
        
        temp_path = temp_dir / filename
        final_path = model_path / filename

        # Create parent directories for files in subdirectories
        temp_path.parent.mkdir(parents=True, exist_ok=True)

        url = f"https://huggingface.co/{repo_id}/resolve/main/{filename}"
        self.logger.debug(f"[DOWNLOAD THREAD] URL: {url}")
        
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        # Check if we can resume a partial download
        resume_from = 0
        file_mode = "wb"
        if temp_path.exists():
            existing_size = temp_path.stat().st_size
            if existing_size > 0 and existing_size < file_size:
                # Attempt to resume from where we left off
                resume_from = existing_size
                file_mode = "ab"  # Append mode
                headers["Range"] = f"bytes={existing_size}-"
                self.logger.info(
                    f"Resuming download of {filename} from byte {existing_size}"
                )
            elif existing_size >= file_size:
                # File already complete in temp, just move it
                self.logger.info(
                    f"Temp file {filename} already complete, moving to final location"
                )
                try:
                    final_path.parent.mkdir(parents=True, exist_ok=True)
                    if final_path.exists():
                        final_path.unlink()
                    temp_path.rename(final_path)
                    self._mark_file_complete(filename)
                    return
                except Exception as e:
                    self.logger.error(f"Failed to move complete temp file {filename}: {e}")
                    # Fall through to re-download

        try:
            with requests.get(
                url, headers=headers, stream=True, timeout=30
            ) as response:
                # Check if server supports range requests
                if resume_from > 0:
                    if response.status_code == 206:
                        # Partial content - resume successful
                        self.logger.info(f"Server accepted range request for {filename}")
                    elif response.status_code == 200:
                        # Server doesn't support range requests, start over
                        self.logger.warning(
                            f"Server doesn't support range requests for {filename}, restarting download"
                        )
                        resume_from = 0
                        file_mode = "wb"
                    else:
                        response.raise_for_status()
                else:
                    response.raise_for_status()

                content_length = response.headers.get("content-length")
                if content_length:
                    remaining_size = int(content_length)
                    total_file_size = resume_from + remaining_size
                    with self._lock:
                        # Update total_size if bootstrap had 0 for this file
                        old_file_size = self._file_sizes.get(filename, 0)
                        if old_file_size == 0 and total_file_size > 0:
                            self._total_size += total_file_size
                        elif old_file_size != total_file_size:
                            # Adjust total_size for the difference
                            self._total_size += (total_file_size - old_file_size)
                        self._file_sizes[filename] = total_file_size
                else:
                    total_file_size = file_size

                downloaded = resume_from
                with open(temp_path, file_mode) as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if self.is_cancelled:
                            f.close()
                            # Don't delete temp file on cancel - can resume later
                            return

                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

                            if downloaded % (1024 * 1024) < 8192:
                                self._update_file_progress(
                                    filename, downloaded, total_file_size
                                )

                self._update_file_progress(filename, downloaded, total_file_size)

                # Verify download is complete
                if downloaded < file_size:
                    self.logger.error(
                        f"Download incomplete for {filename}: {downloaded} bytes vs expected {file_size}"
                    )
                    self._mark_file_failed(filename)
                    return

                final_path.parent.mkdir(parents=True, exist_ok=True)
                if final_path.exists():
                    final_path.unlink()
                temp_path.rename(final_path)

                self._mark_file_complete(filename)

        except Exception as e:
            import traceback
            self.logger.error(f"Failed to download {filename}: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            self.emit_signal(
                SignalCode.UPDATE_DOWNLOAD_LOG,
                {"message": f"✗ Error downloading {filename}: {e}"},
            )
            self._mark_file_failed(filename)
            # Don't delete temp file - can resume later
