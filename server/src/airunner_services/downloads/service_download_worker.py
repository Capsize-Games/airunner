"""Worker bridge that routes legacy download requests through the service."""

from __future__ import annotations

import time
from typing import Any

from airunner_services.downloads.job_service import DownloadJobService
from airunner_services.utils.application.enum_resolver import signal_code_proxy
from airunner_services.utils.job_tracker import JobStatus
from airunner_services.workers.worker import Worker

SignalCode = signal_code_proxy(
    {
        "CANCEL_HUGGINGFACE_DOWNLOAD": "cancel_huggingface_download",
        "HUGGINGFACE_DOWNLOAD_COMPLETE": "huggingface_download_complete",
        "HUGGINGFACE_DOWNLOAD_FAILED": "huggingface_download_failed",
        "UPDATE_DOWNLOAD_LOG": "update_download_log",
        "UPDATE_DOWNLOAD_PROGRESS": "update_download_progress",
    }
)


class ServiceDownloadWorker(Worker):
    """Bridge the legacy worker interface onto DownloadJobService."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._download_job_service = DownloadJobService()
        self._active_job_id: str | None = None
        self._active_payload: dict[str, Any] | None = None
        self.register(SignalCode.CANCEL_HUGGINGFACE_DOWNLOAD, self.cancel)

    def handle_message(self, message: Any) -> None:
        """Start one service-owned download job for the queued payload."""
        if not isinstance(message, dict):
            return

        self._active_payload = dict(message)
        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {"message": self._start_message(self._active_payload)},
        )

        try:
            self._active_job_id = self._start_job(self._active_payload)
        except Exception as exc:
            self.emit_signal(
                SignalCode.HUGGINGFACE_DOWNLOAD_FAILED,
                {"error": str(exc)},
            )
            return

        self._monitor_job(self._active_job_id, self._active_payload)

    def cancel(self) -> None:
        """Cancel the current service-owned download job when one exists."""
        if self._active_job_id:
            self._download_job_service.cancel_sync(self._active_job_id)

    def _start_job(self, payload: dict[str, Any]) -> str:
        """Start one job for the legacy payload shape."""
        model_type = str(payload.get("model_type") or "llm")
        if model_type == "openvoice_zip":
            zip_url = str(payload.get("zip_url") or "")
            output_dir = str(payload.get("output_dir") or "")
            if not zip_url or not output_dir:
                raise ValueError(
                    "OpenVoice ZIP downloads require url and output"
                )
            return self._download_job_service.start_url_download_sync(
                zip_url,
                output_dir=output_dir,
                extract_zip=True,
            )

        repo_id = str(payload.get("repo_id") or "")
        if not repo_id:
            raise ValueError("Download payload is missing repo_id")
        return self._download_job_service.start_huggingface_download_sync(
            repo_id=repo_id,
            model_type=model_type,
            output_dir=payload.get("output_dir"),
            missing_files=payload.get("missing_files"),
            gguf_filename=payload.get("gguf_filename"),
        )

    def _monitor_job(self, job_id: str, payload: dict[str, Any]) -> None:
        """Poll one download job and mirror its lifecycle onto worker signals."""
        last_progress = -1.0

        while True:
            job = self._download_job_service.get_status_sync(job_id)
            if job is None:
                self.emit_signal(
                    SignalCode.HUGGINGFACE_DOWNLOAD_FAILED,
                    {"error": "Download job not found"},
                )
                return

            if job.progress != last_progress:
                last_progress = job.progress
                self.emit_signal(
                    SignalCode.UPDATE_DOWNLOAD_PROGRESS,
                    {"progress": job.progress},
                )

            if job.status is JobStatus.COMPLETED:
                self.emit_signal(
                    SignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE,
                    self._completion_payload(payload, job.result or {}),
                )
                return
            if job.status is JobStatus.FAILED:
                self.emit_signal(
                    SignalCode.HUGGINGFACE_DOWNLOAD_FAILED,
                    {"error": job.error or "Download failed"},
                )
                return
            if job.status is JobStatus.CANCELLED:
                self.emit_signal(
                    SignalCode.HUGGINGFACE_DOWNLOAD_FAILED,
                    {"error": "Download cancelled"},
                )
                return

            time.sleep(0.1)

    def _completion_payload(
        self,
        payload: dict[str, Any],
        result: dict[str, Any],
    ) -> dict[str, Any]:
        """Return the legacy completion payload expected by callers."""
        paths = result.get("paths") or []
        model_path = paths[0] if paths else payload.get("output_dir", "")
        complete_data = {
            "repo_id": payload.get("repo_id", ""),
            "model_path": model_path,
            "model_type": payload.get("model_type", "llm"),
        }
        pipeline_action = payload.get("pipeline_action")
        if pipeline_action:
            complete_data["pipeline_action"] = pipeline_action
        return complete_data

    @staticmethod
    def _start_message(payload: dict[str, Any]) -> str:
        """Return one user-facing start message for a download payload."""
        if payload.get("model_type") == "openvoice_zip":
            return "Starting download: OpenVoice converter checkpoints"
        repo_id = payload.get("repo_id") or "unknown"
        return f"Starting download: {repo_id}"


__all__ = ["ServiceDownloadWorker"]
