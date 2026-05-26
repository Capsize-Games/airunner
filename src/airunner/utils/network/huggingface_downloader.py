from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import QObject, Signal

from airunner.daemon_client.gui_daemon_client import GuiDaemonClient
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.components.application.gui.windows.main.settings_mixin import (
    SettingsMixin,
)


class HuggingfaceDownloader(
    MediatorMixin,
    SettingsMixin,
    QObject,
):
    completed = Signal()

    def __init__(
        self,
        callback: Optional[Callable[[int, int], None]] = None,
        headless: bool = False,
        daemon_client: Optional[GuiDaemonClient] = None,
    ):
        """Initialize one GUI downloader backed by daemon jobs."""
        super().__init__()
        self._default_callback = callback
        self._daemon_client = daemon_client
        self._active_job_id: Optional[str] = None
        self.downloading = False
        self.headless = headless

    def _client(self) -> GuiDaemonClient:
        """Return the daemon client used for service-owned downloads."""
        if self._daemon_client is not None:
            return self._daemon_client

        api = getattr(self, "api", None)
        daemon_client = getattr(api, "daemon_client", None)
        if daemon_client is None:
            daemon_client = GuiDaemonClient()

        self._daemon_client = daemon_client
        return daemon_client

    @staticmethod
    def _progress_reporter(
        callback: Optional[Callable[[int, int], None]],
    ) -> Callable[[dict], None]:
        """Return one job-status callback compatible with GUI progress."""

        def report(status: dict) -> None:
            if callback is None:
                return

            progress = float(status.get("progress") or 0.0)
            clamped = max(0, min(100, int(round(progress))))
            callback(clamped, 100)

        return report

    def download_model(
        self,
        requested_path: str,
        requested_file_name: str,
        requested_file_path: str,
        requested_callback: Callable[[int, int], None],
    ) -> None:
        """Download one HuggingFace file through the daemon service."""
        output_dir = str(Path(requested_file_path).expanduser())
        callback = requested_callback or self._default_callback
        daemon_client = self._client()
        self.downloading = True

        job = daemon_client.start_huggingface_file_download(
            repo_id=requested_path,
            filename=requested_file_name,
            output_dir=output_dir,
        )
        self._active_job_id = str(job.get("job_id") or "")
        if not self._active_job_id:
            raise RuntimeError("Daemon did not return a download job id")

        try:
            daemon_client.wait_download_job(
                self._active_job_id,
                progress_callback=self._progress_reporter(callback),
            )
            if callback is not None:
                callback(100, 100)
        finally:
            self._active_job_id = None
            self.downloading = False

        self.handle_completed()

    def handle_completed(self) -> None:
        """Emit one completion signal for the active download."""
        self.completed.emit()

    def stop_download(self) -> None:
        """Cancel the active daemon-backed download when one exists."""
        if not self._active_job_id:
            return

        self._client().cancel_download_job(self._active_job_id)
