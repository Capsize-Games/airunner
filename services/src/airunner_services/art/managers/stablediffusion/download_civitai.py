"""Service-owned CivitAI download compatibility wrapper."""

import os
import threading
import time
from typing import Callable, Optional

from airunner_services.downloads.civitai import fetch_model_info
from airunner_services.downloads.job_service import DownloadJobService
from airunner_services.utils.job_tracker import JobState, JobStatus
from airunner_services.utils.application.mediator_mixin import MediatorMixin
from airunner_services.utils.application.runtime_context_mixin import (
    RuntimeContextMixin,
)


ProgressCallback = Callable[[int, int], None]


class DownloadCivitAI(RuntimeContextMixin, MediatorMixin):
    """Bridge legacy CivitAI downloads onto the shared service job API."""

    def __init__(self) -> None:
        """Initialize one compatibility wrapper around DownloadJobService."""
        super().__init__()
        self._download_job_service = DownloadJobService()
        self._active_job_id: Optional[str] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_requested = threading.Event()
        self.file_name: Optional[str] = None

    def get_json(self, model_id: str) -> Optional[dict]:
        """Return one CivitAI model metadata payload by numeric id."""
        normalized_id = str(model_id).split("/", 1)[0]
        try:
            return fetch_model_info(normalized_id, self._api_key())
        except Exception:
            self.logger.exception(
                "Failed to fetch CivitAI model metadata for %s",
                normalized_id,
            )
            return None

    def download_model(
        self,
        url: str,
        file_name: str,
        size_kb: int,
        callback: Optional[ProgressCallback],
    ) -> None:
        """Start one CivitAI download through DownloadJobService."""
        self.file_name = os.path.expanduser(file_name)
        self._stop_requested = threading.Event()
        file_size = max(0, int(size_kb) * 1024)
        self._active_job_id = (
            self._download_job_service.start_civitai_file_download_sync(
                url,
                output_path=self.file_name,
                file_size=file_size,
                api_key=self._api_key(),
            )
        )
        self._monitor_thread = threading.Thread(
            target=self._monitor_download,
            args=(self._active_job_id, file_size, callback),
            daemon=True,
        )
        self._monitor_thread.start()

    def remove_file(self) -> None:
        """Delete one partially downloaded file when it still exists."""
        if self.file_name and os.path.exists(self.file_name):
            os.remove(self.file_name)
            self.logger.info(
                "Cancelled CivitAI download removed partial file %s",
                self.file_name,
            )

    def stop_download(self) -> None:
        """Request cancellation for the active CivitAI download."""
        self._stop_requested.set()
        if self._active_job_id:
            self._download_job_service.cancel_sync(self._active_job_id)

    def _monitor_download(
        self,
        job_id: str,
        file_size: int,
        callback: Optional[ProgressCallback],
    ) -> None:
        """Mirror service job progress onto the legacy callback contract."""
        last_current = -1
        while not self._stop_requested.is_set():
            job = self._download_job_service.get_status_sync(job_id)
            if job is None:
                self._fail_download("Download job not found")
                return
            current = self._current_bytes(job.progress, file_size)
            if callback is not None and current != last_current:
                last_current = current
                callback(current, file_size)
            if job.status in self._terminal_statuses():
                self._handle_terminal_job(job)
                return
            time.sleep(0.1)

    def _handle_terminal_job(self, job: JobState) -> None:
        """Handle completion, failure, or cancellation for one job."""
        if job.status is JobStatus.COMPLETED:
            self._notify_download_complete()
        elif job.status is JobStatus.CANCELLED:
            self.remove_file()
        else:
            self._fail_download(job.error or "Download failed")
        self._active_job_id = None

    def _notify_download_complete(self) -> None:
        """Notify the active API when one download completes."""
        download_complete = getattr(
            getattr(self, "api", None),
            "download_complete",
            None,
        )
        if callable(download_complete):
            download_complete(self.file_name or "")

    def _fail_download(self, message: str) -> None:
        """Log one failed download and remove any remaining partial file."""
        self.logger.error("CivitAI download failed: %s", message)
        self.remove_file()

    def _api_key(self) -> str:
        """Return the configured CivitAI API key."""
        return str(
            getattr(self.application_settings, "civit_ai_api_key", "")
            or ""
        )

    @staticmethod
    def _current_bytes(progress: float, file_size: int) -> int:
        """Convert one progress percentage into current bytes."""
        if file_size <= 0:
            return 0
        progress = max(0.0, min(100.0, float(progress)))
        return int(round((progress / 100.0) * file_size))

    @staticmethod
    def _terminal_statuses() -> tuple[JobStatus, ...]:
        """Return the terminal job states for CivitAI downloads."""
        return (
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        )


class CivitAIDownloader:
    """
    Simple downloader for CivitAI models for testability and modularity.
    """

    def download(self, model_id: str, version: str) -> str:
        """
        Download a model from CivitAI.
        Args:
            model_id: The model ID on CivitAI.
            version: The version to download.
        Returns:
            str: Path to the downloaded model file.
        """
        # In real code, implement actual download logic
        # Here, just a stub for testability
        return f"/models/{model_id}/{version}/model.safetensors"


def download_model(model_id: str, version: str) -> str:
    """
    Download a model from CivitAI using CivitAIDownloader.
    Args:
        model_id: The model ID on CivitAI.
        version: The version to download.
    Returns:
        str: Path to the downloaded model file.
    """
    downloader = CivitAIDownloader()
    return downloader.download(model_id, version)
