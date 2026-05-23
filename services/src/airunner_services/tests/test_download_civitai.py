"""Tests for the service-owned CivitAI download compatibility wrapper."""

from __future__ import annotations

from types import SimpleNamespace

from airunner_services.art.managers.stablediffusion.download_civitai import (
    DownloadCivitAI,
)
from airunner_services.utils.job_tracker import JobState, JobStatus


class FakeDownloadJobService:
    """Minimal job-service double for CivitAI download tests."""

    def __init__(self, jobs: list[JobState] | None = None) -> None:
        self._jobs = list(jobs or [])
        self.cancelled_job_ids: list[str] = []
        self.started: list[dict[str, object]] = []

    def start_civitai_file_download_sync(
        self,
        url: str,
        *,
        output_path: str,
        file_size: int,
        api_key: str,
    ) -> str:
        self.started.append(
            {
                "url": url,
                "output_path": output_path,
                "file_size": file_size,
                "api_key": api_key,
            }
        )
        return "job-1"

    def get_status_sync(self, _job_id: str):
        if self._jobs:
            return self._jobs.pop(0)
        return JobState(job_id="job-1", status=JobStatus.COMPLETED, progress=100.0)

    def cancel_sync(self, job_id: str) -> bool:
        self.cancelled_job_ids.append(job_id)
        return True


def test_get_json_uses_service_fetch_helper(monkeypatch) -> None:
    """The wrapper should resolve metadata through the service helper."""
    recorded: list[tuple[str, str]] = []

    monkeypatch.setattr(
        "airunner_services.art.managers.stablediffusion.download_civitai.fetch_model_info",
        lambda model_id, api_key: recorded.append((model_id, api_key)) or {"id": model_id},
    )
    monkeypatch.setattr(
        DownloadCivitAI,
        "application_settings",
        property(lambda self: SimpleNamespace(civit_ai_api_key="secret")),
    )

    downloader = DownloadCivitAI()

    assert downloader.get_json("123/example-model") == {"id": "123"}
    assert recorded == [("123", "secret")]


def test_download_model_uses_service_job_and_reports_progress(
    monkeypatch,
    tmp_path,
) -> None:
    """The wrapper should mirror job progress onto the legacy callback."""
    job_service = FakeDownloadJobService(
        jobs=[
            JobState(job_id="job-1", status=JobStatus.RUNNING, progress=25.0),
            JobState(job_id="job-1", status=JobStatus.COMPLETED, progress=100.0),
        ]
    )
    progress_updates: list[tuple[int, int]] = []
    completed: list[str] = []

    monkeypatch.setattr(
        "airunner_services.art.managers.stablediffusion.download_civitai.time.sleep",
        lambda _seconds: None,
    )
    monkeypatch.setattr(
        DownloadCivitAI,
        "application_settings",
        property(lambda self: SimpleNamespace(civit_ai_api_key="secret")),
    )

    downloader = DownloadCivitAI()
    downloader._download_job_service = job_service
    downloader.api = SimpleNamespace(
        download_complete=lambda file_name: completed.append(file_name)
    )
    file_name = str(tmp_path / "model.safetensors")

    downloader.download_model(
        "https://example.com/model",
        file_name,
        1,
        lambda current, total: progress_updates.append((current, total)),
    )
    downloader._monitor_thread.join(timeout=1.0)

    assert job_service.started == [
        {
            "url": "https://example.com/model",
            "output_path": file_name,
            "file_size": 1024,
            "api_key": "secret",
        }
    ]
    assert progress_updates[0] == (256, 1024)
    assert progress_updates[-1] == (1024, 1024)
    assert completed == [file_name]


def test_stop_download_cancels_active_job(monkeypatch) -> None:
    """Stopping the wrapper should cancel the tracked service job."""
    monkeypatch.setattr(
        DownloadCivitAI,
        "application_settings",
        property(lambda self: SimpleNamespace(civit_ai_api_key="secret")),
    )
    downloader = DownloadCivitAI()
    downloader._download_job_service = FakeDownloadJobService()
    downloader._active_job_id = "job-1"

    downloader.stop_download()

    assert downloader._download_job_service.cancelled_job_ids == ["job-1"]