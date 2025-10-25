"""Worker for HuggingFace model downloads using Python threading."""

import os
import threading
from pathlib import Path
from typing import Dict, Any
import requests

from airunner.components.application.workers.worker import Worker
from airunner.enums import SignalCode, QueueType
from airunner.components.llm.utils.model_downloader import (
    HuggingFaceDownloader,
)
from airunner.utils.settings.get_qsettings import get_qsettings


class HuggingFaceDownloadWorker(Worker):
    """Worker for downloading HuggingFace models with parallel file downloading."""

    queue_type = QueueType.GET_NEXT_ITEM

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.downloader = HuggingFaceDownloader()
        self._model_path = None
        self._temp_dir = None
        self._total_downloaded = 0
        self._total_size = 0
        self._file_threads: Dict[str, threading.Thread] = {}
        self._file_progress: Dict[str, int] = {}
        self._file_sizes: Dict[str, int] = {}
        self._completed_files = set()
        self._failed_files = set()
        self._lock = threading.Lock()
        self.is_cancelled = False

    def handle_message(self, message: Any):
        """Process download request from queue."""
        repo_id = message.get("repo_id")
        model_type = message.get("model_type", "llm")
        output_dir = message.get("output_dir")

        try:
            self._download_model(repo_id, model_type, output_dir)
        except Exception as e:
            self.logger.error(f"Download failed: {e}")
            self.emit_signal(
                SignalCode.HUGGINGFACE_DOWNLOAD_FAILED, {"error": str(e)}
            )

    def _download_model(self, repo_id: str, model_type: str, output_dir: str):
        """Download model files."""
        self.is_cancelled = False
        self._completed_files.clear()
        self._failed_files.clear()
        self._file_progress.clear()
        self._file_sizes.clear()
        self._file_threads.clear()

        settings = get_qsettings()
        api_key = settings.value("huggingface/api_key", "")

        if not output_dir:
            from airunner.settings import MODELS_DIR

            output_dir = os.path.join(MODELS_DIR, "text/models/llm/causallm")

        model_name = repo_id.split("/")[-1]
        model_path = Path(output_dir) / model_name
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
            self.emit_signal(
                SignalCode.HUGGINGFACE_DOWNLOAD_FAILED, {"error": str(e)}
            )
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
                SignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE,
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
                    temp_dir,
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

        while not self.is_cancelled:
            all_done = len(self._completed_files) + len(
                self._failed_files
            ) == len(files_to_download)
            if all_done:
                break
            threading.Event().wait(0.1)

        if self.is_cancelled:
            self.emit_signal(
                SignalCode.UPDATE_DOWNLOAD_LOG,
                {"message": "Download cancelled by user"},
            )
            self._cleanup_temp_files()
            return

        if self._failed_files:
            error_msg = f"Failed to download {len(self._failed_files)} files"
            self.emit_signal(
                SignalCode.HUGGINGFACE_DOWNLOAD_FAILED, {"error": error_msg}
            )
            return

        self._cleanup_temp_files()
        self.emit_signal(
            SignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE,
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
        """Download a single file (runs in Python thread)."""
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

                with self._lock:
                    self._completed_files.add(filename)

                self.emit_signal(
                    SignalCode.UPDATE_DOWNLOAD_LOG,
                    {"message": f"✓ Completed {filename}"},
                )

        except Exception as e:
            self.logger.error(f"Failed to download {filename}: {e}")
            with self._lock:
                self._failed_files.add(filename)

            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass

    def _update_file_progress(
        self, filename: str, downloaded: int, total: int
    ):
        """Update progress for a single file."""
        with self._lock:
            old_progress = self._file_progress.get(filename, 0)
            self._file_progress[filename] = downloaded
            self._total_downloaded += downloaded - old_progress

        self.emit_signal(
            SignalCode.UPDATE_FILE_DOWNLOAD_PROGRESS,
            {"filename": filename, "downloaded": downloaded, "total": total},
        )

        if self._total_size > 0:
            overall_progress = (
                self._total_downloaded / self._total_size
            ) * 100.0
            self.emit_signal(
                SignalCode.UPDATE_DOWNLOAD_PROGRESS,
                {"progress": overall_progress},
            )

    def _cleanup_temp_files(self):
        """Clean up temporary download directory."""
        if self._temp_dir and self._temp_dir.exists():
            try:
                import shutil

                shutil.rmtree(self._temp_dir)
                self.emit_signal(
                    SignalCode.UPDATE_DOWNLOAD_LOG,
                    {"message": "Cleaned up temporary files"},
                )
            except Exception as e:
                self.logger.error(f"Failed to cleanup temp files: {e}")

    def cancel(self):
        """Cancel the current download."""
        self.logger.info("Cancelling all downloads...")
        self.is_cancelled = True
        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {"message": "Cancelling all downloads..."},
        )
