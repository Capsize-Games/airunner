"""Abstract base class for model download workers.

This module provides the common interface and shared functionality for all
model download workers (HuggingFace, CivitAI, etc.).
"""

import shutil
import threading
from abc import abstractmethod
from pathlib import Path
from typing import Dict, Set, Any

from airunner.components.application.workers.worker import Worker
from airunner.enums import SignalCode, QueueType


class BaseDownloadWorker(Worker):
    """Abstract base class for model download workers.

    Provides common functionality for:
    - Parallel file downloads
    - Progress tracking (overall and per-file)
    - Download cancellation
    - Temporary file management
    - Thread-safe state management

    Subclasses must implement:
    - _download_model() - Provider-specific download logic
    - _download_file() - Provider-specific file download
    - _complete_signal - SignalCode for download complete
    - _failed_signal - SignalCode for download failed
    """

    queue_type = QueueType.GET_NEXT_ITEM

    def __init__(self, *args, **kwargs):
        """Initialize the download worker.

        Args:
            *args: Positional arguments for Worker
            **kwargs: Keyword arguments for Worker
        """
        super().__init__(*args, **kwargs)
        self._model_path = None
        self._temp_dir = None
        self._total_downloaded = 0
        self._total_size = 0
        self._file_threads: Dict[str, threading.Thread] = {}
        self._file_progress: Dict[str, int] = {}
        self._file_sizes: Dict[str, int] = {}
        self._completed_files: Set[str] = set()
        self._failed_files: Set[str] = set()
        self._lock = threading.Lock()
        self.is_cancelled = False

    @property
    @abstractmethod
    def _complete_signal(self) -> SignalCode:
        """Signal to emit on successful download completion.

        Returns:
            SignalCode for download complete (e.g., HUGGINGFACE_DOWNLOAD_COMPLETE)
        """

    @property
    @abstractmethod
    def _failed_signal(self) -> SignalCode:
        """Signal to emit on download failure.

        Returns:
            SignalCode for download failed (e.g., HUGGINGFACE_DOWNLOAD_FAILED)
        """

    @abstractmethod
    def _download_model(self, **kwargs):
        """Download the model (provider-specific logic).

        This method should:
        1. Get list of files to download
        2. Create download threads
        3. Wait for completion
        4. Handle errors and cancellation
        5. Emit completion or failure signal

        Args:
        **kwargs: Provider-specific arguments (repo_id, model_id, etc.)
        """

    @abstractmethod
    def _download_file(self, **kwargs):
        """Download a single file (runs in Python thread).

        This method should:
        1. Download file with streaming
        2. Save to temporary location
        3. Update progress periodically
        4. Move to final location on success
        5. Handle errors and cancellation

        Args:
            **kwargs: File-specific arguments (url, filename, etc.)
        """

    def handle_message(self, message: Any):
        """Process download request from queue.

        Args:
            message: Download request with provider-specific parameters
        """
        self.logger.info(f"BaseDownloadWorker handling message: {message}")
        try:
            self._download_model(**message)
        except Exception as e:
            self.logger.error(f"Download failed: {e}")
            import traceback

            self.logger.error(traceback.format_exc())
            self.emit_signal(self._failed_signal, {"error": str(e)})

    def _update_file_progress(
        self, filename: str, downloaded: int, total: int
    ):
        """Update progress for a single file.

        Thread-safe progress update that:
        1. Updates per-file progress
        2. Updates overall downloaded bytes
        3. Emits per-file progress signal
        4. Emits overall progress signal

        Args:
            filename: Name of the file being downloaded
            downloaded: Bytes downloaded so far
            total: Total bytes for this file
        """
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
        """Clean up temporary download directory.

        Removes the .downloading directory after successful completion
        or cancellation.
        """
        if self._temp_dir and self._temp_dir.exists():
            try:
                shutil.rmtree(self._temp_dir)
                self.emit_signal(
                    SignalCode.UPDATE_DOWNLOAD_LOG,
                    {"message": "Cleaned up temporary files"},
                )
            except Exception as e:
                self.logger.error(f"Failed to cleanup temp files: {e}")

    def _initialize_download(self, output_dir: str, model_name: str) -> Path:
        """Initialize download state and create directories.

        Args:
            output_dir: Base output directory
            model_name: Name of the model (for subdirectory)

        Returns:
            Path to the model directory
        """
        self.is_cancelled = False
        self._completed_files.clear()
        self._failed_files.clear()
        self._file_progress.clear()
        self._file_sizes.clear()
        self._file_threads.clear()
        self._total_downloaded = 0
        self._total_size = 0

        model_path = Path(output_dir) / model_name
        temp_dir = model_path / ".downloading"
        temp_dir.mkdir(parents=True, exist_ok=True)

        self._model_path = model_path
        self._temp_dir = temp_dir

        return model_path

    def _start_download_threads(
        self, files_to_download: list, download_fn, *args
    ):
        """Start download threads for multiple files.

        Args:
            files_to_download: List of file info dicts
            download_fn: Function to call for each file
            *args: Additional arguments to pass to download_fn
        """
        for file_info in files_to_download:
            if self.is_cancelled:
                return

            filename = file_info["filename"]
            file_size = file_info.get("size", 0)

            self._file_sizes[filename] = file_size
            self._file_progress[filename] = 0

            self.emit_signal(
                SignalCode.UPDATE_DOWNLOAD_LOG,
                {"message": f"Starting download for {filename}..."},
            )

            thread = threading.Thread(
                target=download_fn,
                args=(filename, file_size, *args),
                daemon=True,
            )
            self._file_threads[filename] = thread
            thread.start()

    def _wait_for_completion(self, expected_count: int):
        """Wait for all download threads to complete.

        Args:
            expected_count: Number of files expected to download

        Returns:
            True if all files completed successfully, False otherwise
        """
        while not self.is_cancelled:
            all_done = (
                len(self._completed_files) + len(self._failed_files)
                == expected_count
            )
            if all_done:
                break
            threading.Event().wait(0.1)

        if self.is_cancelled:
            self.emit_signal(
                SignalCode.UPDATE_DOWNLOAD_LOG,
                {"message": "Download cancelled by user"},
            )
            self._cleanup_temp_files()
            return False

        if self._failed_files:
            error_msg = (
                f"Failed to download {len(self._failed_files)} files: "
                f"{', '.join(list(self._failed_files)[:5])}"
            )
            self.emit_signal(self._failed_signal, {"error": error_msg})
            return False

        return True

    def _mark_file_complete(self, filename: str):
        """Mark a file as successfully downloaded.

        Thread-safe method to add file to completed set.

        Args:
            filename: Name of the completed file
        """
        with self._lock:
            self._completed_files.add(filename)

        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {"message": f"✓ Completed {filename}"},
        )

    def _mark_file_failed(self, filename: str):
        """Mark a file as failed to download.

        Thread-safe method to add file to failed set.

        Args:
            filename: Name of the failed file
        """
        with self._lock:
            self._failed_files.add(filename)

    def cancel(self):
        """Cancel the current download.

        Sets cancellation flag which is checked by download threads.
        """
        self.logger.info("Cancelling all downloads...")
        self.is_cancelled = True
        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {"message": "Cancelling all downloads..."},
        )
