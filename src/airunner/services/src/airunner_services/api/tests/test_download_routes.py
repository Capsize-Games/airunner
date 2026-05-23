"""Tests for the service-owned download job routes."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from airunner_services.utils.job_tracker import JobState, JobStatus


class FakeDownloadJobService:
    """Minimal async service double for download route tests."""

    def __init__(self) -> None:
        self.started = []
        self.hf_file_started = []
        self.civitai_file_started = []
        self.url_started = []
        self.cancelled = []
        self.jobs = {
            "job-1": JobState(
                job_id="job-1",
                status=JobStatus.RUNNING,
                progress=25.0,
                metadata={"provider": "huggingface"},
            )
        }

    async def start_huggingface_download(self, **kwargs) -> str:
        self.started.append(kwargs)
        return "job-1"

    async def start_huggingface_file_download(
        self,
        repo_id: str,
        filename: str,
        **kwargs,
    ) -> str:
        self.hf_file_started.append((repo_id, filename, kwargs))
        return "job-file-1"

    async def start_civitai_file_download(
        self,
        url: str,
        **kwargs,
    ) -> str:
        self.civitai_file_started.append((url, kwargs))
        return "job-civitai-1"

    async def start_url_download(self, url: str, **kwargs) -> str:
        self.url_started.append((url, kwargs))
        return "job-url-1"

    async def get_status(self, job_id: str):
        return self.jobs.get(job_id)

    async def cancel(self, job_id: str) -> bool:
        self.cancelled.append(job_id)
        job = self.jobs.get(job_id)
        if job is None:
            return False
        job.status = JobStatus.CANCELLED
        return True


def _request_for(service: FakeDownloadJobService):
    return SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(download_job_service=service)
        )
    )


def test_start_huggingface_download_queues_service_job() -> None:
    from airunner_api.routes.downloads import (
        HuggingFaceDownloadRequest,
        start_huggingface_download,
    )

    service = FakeDownloadJobService()

    response = asyncio.run(
        start_huggingface_download(
            HuggingFaceDownloadRequest(
                repo_id="example/model",
                model_type="art",
                output_dir="/tmp/model",
                missing_files=["config.json"],
            ),
            _request_for(service),
        )
    )

    assert response.job_id == "job-1"
    assert service.started == [
        {
            "repo_id": "example/model",
            "model_type": "art",
            "output_dir": "/tmp/model",
            "missing_files": ["config.json"],
            "gguf_filename": None,
            "prefer_pre_quantized": True,
        }
    ]


def test_start_huggingface_file_download_queues_service_job() -> None:
    from airunner_api.routes.downloads import (
        HuggingFaceFileDownloadRequest,
        start_huggingface_file_download,
    )

    service = FakeDownloadJobService()

    response = asyncio.run(
        start_huggingface_file_download(
            HuggingFaceFileDownloadRequest(
                repo_id="example/model",
                filename="config.json",
                output_dir="/tmp/model",
            ),
            _request_for(service),
        )
    )

    assert response.job_id == "job-file-1"
    assert service.hf_file_started == [
        (
            "example/model",
            "config.json",
            {"output_dir": "/tmp/model"},
        )
    ]


def test_get_download_job_status_returns_serialized_job() -> None:
    from airunner_api.routes.downloads import get_download_job_status

    service = FakeDownloadJobService()

    response = asyncio.run(
        get_download_job_status("job-1", _request_for(service))
    )

    assert response.job_id == "job-1"
    assert response.status == "running"
    assert response.progress == 25.0
    assert response.metadata == {"provider": "huggingface"}


def test_start_url_download_queues_service_job() -> None:
    from airunner_api.routes.downloads import (
        UrlDownloadRequest,
        start_url_download,
    )

    service = FakeDownloadJobService()

    response = asyncio.run(
        start_url_download(
            UrlDownloadRequest(
                url="https://example.com/archive.zip",
                output_dir="/tmp/openvoice",
                extract_zip=True,
            ),
            _request_for(service),
        )
    )

    assert response.job_id == "job-url-1"
    assert service.url_started == [
        (
            "https://example.com/archive.zip",
            {
                "output_dir": "/tmp/openvoice",
                "filename": None,
                "extract_zip": True,
            },
        )
    ]


def test_start_civitai_file_download_queues_service_job() -> None:
    from airunner_api.routes.downloads import (
        CivitaiFileDownloadRequest,
        start_civitai_file_download,
    )

    service = FakeDownloadJobService()

    response = asyncio.run(
        start_civitai_file_download(
            CivitaiFileDownloadRequest(
                url="https://civitai.com/api/download/models/123",
                output_path="/tmp/model.safetensors",
                file_size=1024,
                api_key="token",
            ),
            _request_for(service),
        )
    )

    assert response.job_id == "job-civitai-1"
    assert service.civitai_file_started == [
        (
            "https://civitai.com/api/download/models/123",
            {
                "output_path": "/tmp/model.safetensors",
                "file_size": 1024,
                "api_key": "token",
            },
        )
    ]


def test_fetch_civitai_model_info_returns_service_payload(
    monkeypatch,
) -> None:
    from airunner_api.routes import downloads as download_routes

    monkeypatch.setattr(
        download_routes,
        "fetch_civitai_model_info_service",
        lambda url, api_key="": {
            "url": url,
            "api_key": api_key,
            "modelVersions": [],
        },
    )

    response = asyncio.run(
        download_routes.fetch_civitai_model_info_route(
            download_routes.CivitaiModelInfoRequest(
                url="https://civitai.com/models/123/example",
                api_key="token",
            )
        )
    )

    assert response == {
        "url": "https://civitai.com/models/123/example",
        "api_key": "token",
        "modelVersions": [],
    }


def test_cancel_download_job_returns_updated_status() -> None:
    from airunner_api.routes.downloads import cancel_download_job

    service = FakeDownloadJobService()

    response = asyncio.run(
        cancel_download_job("job-1", _request_for(service))
    )

    assert response.job_id == "job-1"
    assert response.status == "cancelled"
    assert service.cancelled == ["job-1"]