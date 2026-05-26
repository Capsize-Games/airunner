"""Daemon-backed GUI worker for HuggingFace download flows."""

from __future__ import annotations

import time
from typing import Any

from airunner.components.application.workers.worker import Worker
from airunner.daemon_client.gui_daemon_client import GuiDaemonClient
from airunner.enums import SignalCode

_POLL_INTERVAL_SECONDS = 0.10


class HuggingFaceDownloadWorker(Worker):
    """Bridge GUI download requests onto daemon-owned download jobs."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._daemon_client: GuiDaemonClient | None = None
        self._active_job_id: str | None = None
        self._active_payload: dict[str, Any] | None = None
        self.register(SignalCode.CANCEL_HUGGINGFACE_DOWNLOAD, self.cancel)

    def handle_message(self, message: Any) -> None:
        """Start one daemon-backed download job for the queued payload."""
        if not isinstance(message, dict):
            return
        payload = dict(message)
        self._active_payload = payload
        try:
            job_id = self._start_job(payload)
        except Exception as exc:
            self._emit_failure(str(exc))
            return
        if not job_id:
            self._emit_failure("Daemon did not return a download job id")
            return
        self._active_job_id = job_id
        try:
            self._monitor_job(job_id, payload)
        finally:
            self._active_job_id = None
            self._active_payload = None

    def cancel(self) -> None:
        """Cancel the active daemon-backed download and clear queued work."""
        super().cancel()
        job_id = self._active_job_id
        if not job_id:
            return
        try:
            self._client().cancel_download_job(job_id)
        except RuntimeError:
            self.logger.debug("Ignoring cancel failure for %s", job_id)

    def _client(self) -> GuiDaemonClient:
        """Return the daemon client used for GUI download requests."""
        if self._daemon_client is not None:
            return self._daemon_client
        api = getattr(self, "api", None)
        daemon_client = getattr(api, "daemon_client", None)
        self._daemon_client = daemon_client or GuiDaemonClient()
        return self._daemon_client

    def _start_job(self, payload: dict[str, Any]) -> str:
        """Queue one daemon-backed job for the legacy worker payload."""
        model_type = str(payload.get("model_type") or "llm")
        if model_type == "openvoice_zip":
            return self._start_url_job(payload)
        repo_id = str(payload.get("repo_id") or "")
        if not repo_id:
            raise ValueError("Download payload is missing repo_id")
        response = self._client().start_huggingface_download(
            repo_id=repo_id,
            model_type=model_type,
            output_dir=payload.get("output_dir"),
            missing_files=payload.get("missing_files"),
            gguf_filename=payload.get("gguf_filename"),
        )
        return str(response.get("job_id") or "")

    def _start_url_job(self, payload: dict[str, Any]) -> str:
        """Queue one daemon-backed ZIP download for OpenVoice setup."""
        zip_url = str(payload.get("zip_url") or "")
        output_dir = str(payload.get("output_dir") or "")
        if not zip_url or not output_dir:
            raise ValueError("OpenVoice ZIP downloads require url and output")
        response = self._client().start_url_download(
            url=zip_url,
            output_dir=output_dir,
            extract_zip=True,
        )
        return str(response.get("job_id") or "")

    def _monitor_job(self, job_id: str, payload: dict[str, Any]) -> None:
        """Poll one daemon download job and mirror its progress signals."""
        last_progress = -1.0
        last_log_message = ""
        last_file_progress: tuple[str, int, int] | None = None

        while True:
            try:
                status = self._client().download_job_status(job_id)
            except RuntimeError as exc:
                self._emit_failure(str(exc))
                return

            last_progress = self._emit_progress_update(status, last_progress)
            last_log_message = self._emit_log_update(status, last_log_message)
            last_file_progress = self._emit_file_progress_update(
                status,
                last_file_progress,
            )
            if self._handle_terminal_status(status, payload):
                return
            time.sleep(_POLL_INTERVAL_SECONDS)

    def _emit_progress_update(
        self,
        status: dict[str, Any],
        last_progress: float,
    ) -> float:
        """Emit one overall progress update when the percent changed."""
        progress = float(status.get("progress") or 0.0)
        if progress == last_progress:
            return last_progress
        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_PROGRESS,
            {"progress": progress},
        )
        return progress

    def _emit_log_update(
        self,
        status: dict[str, Any],
        last_log_message: str,
    ) -> str:
        """Emit one log update when the daemon reports a new message."""
        metadata = self._status_metadata(status)
        message = str(metadata.get("last_log_message") or "")
        if not message or message == last_log_message:
            return last_log_message
        self.emit_signal(SignalCode.UPDATE_DOWNLOAD_LOG, {"message": message})
        return message

    def _emit_file_progress_update(
        self,
        status: dict[str, Any],
        last_file_progress: tuple[str, int, int] | None,
    ) -> tuple[str, int, int] | None:
        """Emit one per-file progress update when the daemon reports one."""
        metadata = self._status_metadata(status)
        data = metadata.get("file_progress")
        if not isinstance(data, dict):
            return last_file_progress
        filename = str(data.get("filename") or "")
        downloaded = max(0, int(data.get("downloaded") or 0))
        total = max(0, int(data.get("total") or 0))
        current = (filename, downloaded, total)
        if not filename or current == last_file_progress:
            return last_file_progress
        self.emit_signal(
            SignalCode.UPDATE_FILE_DOWNLOAD_PROGRESS,
            {
                "filename": filename,
                "downloaded": downloaded,
                "total": total,
            },
        )
        return current

    def _handle_terminal_status(
        self,
        status: dict[str, Any],
        payload: dict[str, Any],
    ) -> bool:
        """Handle one terminal daemon job status when it arrives."""
        state = str(status.get("status") or "").lower()
        if state == "completed":
            self.emit_signal(
                SignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE,
                self._completion_payload(payload, status),
            )
            return True
        if state == "failed":
            self._emit_failure(str(status.get("error") or "Download failed"))
            return True
        if state == "cancelled":
            self._emit_failure("Download cancelled")
            return True
        return False

    def _completion_payload(
        self,
        payload: dict[str, Any],
        status: dict[str, Any],
    ) -> dict[str, Any]:
        """Return the legacy completion payload expected by GUI callers."""
        result = status.get("result")
        result_data = result if isinstance(result, dict) else {}
        paths = result_data.get("paths") or []
        model_path = paths[0] if paths else payload.get("output_dir", "")
        completion = {
            "model_path": model_path,
            "model_type": payload.get("model_type", "llm"),
        }
        repo_id = payload.get("repo_id")
        if repo_id:
            completion["repo_id"] = repo_id
        pipeline_action = payload.get("pipeline_action")
        if pipeline_action:
            completion["pipeline_action"] = pipeline_action
        return completion

    @staticmethod
    def _status_metadata(status: dict[str, Any]) -> dict[str, Any]:
        """Return one normalized metadata mapping from job status."""
        metadata = status.get("metadata")
        if isinstance(metadata, dict):
            return metadata
        return {}

    def _emit_failure(self, error: str) -> None:
        """Emit one GUI failure payload for the active download."""
        self.emit_signal(
            SignalCode.HUGGINGFACE_DOWNLOAD_FAILED,
            {"error": error},
        )


__all__ = ["HuggingFaceDownloadWorker"]