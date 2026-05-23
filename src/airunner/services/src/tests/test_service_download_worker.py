"""Tests for the service-backed legacy download worker bridge."""

from __future__ import annotations

from airunner_services.downloads import service_download_worker
from airunner_services.utils.job_tracker import JobState, JobStatus


class FakeDownloadJobService:
    """Minimal fake for polling one service-backed download job."""

    def __init__(self, states):
        self._states = list(states)
        self.start_calls = []
        self.cancelled = []

    def start_huggingface_download_sync(self, **kwargs):
        self.start_calls.append(("huggingface", kwargs))
        return "job-1"

    def start_url_download_sync(self, url, **kwargs):
        self.start_calls.append(("url", {"url": url, **kwargs}))
        return "job-1"

    def get_status_sync(self, _job_id):
        if len(self._states) > 1:
            return self._states.pop(0)
        return self._states[0]

    def cancel_sync(self, job_id):
        self.cancelled.append(job_id)
        return True


def test_service_download_worker_emits_legacy_completion_payload(
    monkeypatch,
) -> None:
    """HF downloads should keep the completion shape expected by callers."""
    fake_service = FakeDownloadJobService(
        [
            JobState("job-1", JobStatus.RUNNING, progress=25.0),
            JobState(
                "job-1",
                JobStatus.COMPLETED,
                progress=100.0,
                result={"paths": ["/tmp/model"]},
            ),
        ]
    )
    monkeypatch.setattr(
        service_download_worker,
        "DownloadJobService",
        lambda: fake_service,
    )
    worker = service_download_worker.ServiceDownloadWorker()
    events = []
    monkeypatch.setattr(worker, "emit_signal", lambda code, data=None: events.append((code, data)))

    worker.handle_message(
        {
            "repo_id": "example/model",
            "model_type": "art",
            "output_dir": "/tmp/model",
            "pipeline_action": "safety_checker",
        }
    )

    assert fake_service.start_calls == [
        (
            "huggingface",
            {
                "repo_id": "example/model",
                "model_type": "art",
                "output_dir": "/tmp/model",
                "missing_files": None,
                "gguf_filename": None,
            },
        )
    ]
    assert any(data == {"progress": 25.0} for _code, data in events)
    assert any(
        data == {
            "repo_id": "example/model",
            "model_path": "/tmp/model",
            "model_type": "art",
            "pipeline_action": "safety_checker",
        }
        for _code, data in events
    )


def test_service_download_worker_routes_openvoice_zip_through_url_jobs(
    monkeypatch,
) -> None:
    """OpenVoice ZIP downloads should use the generic URL job path."""
    fake_service = FakeDownloadJobService(
        [
            JobState(
                "job-1",
                JobStatus.COMPLETED,
                progress=100.0,
                result={"paths": ["/tmp/openvoice"]},
            )
        ]
    )
    monkeypatch.setattr(
        service_download_worker,
        "DownloadJobService",
        lambda: fake_service,
    )
    worker = service_download_worker.ServiceDownloadWorker()
    events = []
    monkeypatch.setattr(worker, "emit_signal", lambda code, data=None: events.append((code, data)))

    worker.handle_message(
        {
            "model_type": "openvoice_zip",
            "output_dir": "/tmp/openvoice",
            "zip_url": "https://example.com/openvoice.zip",
        }
    )

    assert fake_service.start_calls == [
        (
            "url",
            {
                "url": "https://example.com/openvoice.zip",
                "output_dir": "/tmp/openvoice",
                "extract_zip": True,
            },
        )
    ]
    assert any(
        data == {
            "repo_id": "",
            "model_path": "/tmp/openvoice",
            "model_type": "openvoice_zip",
        }
        for _code, data in events
    )