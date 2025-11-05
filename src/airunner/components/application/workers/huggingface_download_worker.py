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

    def _download_model(self, repo_id: str, model_type: str, output_dir: str):
        """Download model files from HuggingFace.

        Args:
            repo_id: HuggingFace repository ID (e.g., "black-forest-labs/FLUX.1-dev")
            model_type: Type of model (llm, flux, etc.)
            output_dir: Directory to save the model

        """
        settings = get_qsettings()
        api_key = settings.value("huggingface/api_key", "")

        if not output_dir:
            output_dir = os.path.join(MODELS_DIR, "text/models/llm/causallm")

        model_name = repo_id.split("/")[-1]
        model_path = self._initialize_download(output_dir, model_name)

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

            # EXCLUDE consolidated.safetensors - we need individual shards for gradual loading
            if filename == "consolidated.safetensors":
                continue

            # Include required files (config, tokenizer files)
            if filename in required_files:
                files_to_download.append(
                    {"filename": filename, "size": file_info.get("size", 0)}
                )
                continue

            # Include model shards (model-00001-of-00010.safetensors pattern)
            # Include all config/tokenizer files (.json, .txt, .model)
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
