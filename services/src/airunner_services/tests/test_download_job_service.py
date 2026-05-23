"""Tests for the service-owned download job lifecycle."""

from __future__ import annotations

import asyncio
from pathlib import Path
import zipfile

import pytest

from airunner_services.downloads import job_service
from airunner_services.llm.utils import model_downloader
from airunner_services.utils.job_tracker import JobStatus, JobTracker


class FakeResponse:
    """Minimal response double for streamed HuggingFace downloads."""

    def __init__(self, headers=None, chunks=None):
        self.headers = headers or {}
        self._chunks = chunks or []

    def raise_for_status(self) -> None:
        """Mirror the requests response API."""
        return None

    def iter_content(self, chunk_size=8192):
        """Yield the configured download chunks."""
        del chunk_size
        for chunk in self._chunks:
            yield chunk


class FakeHuggingFaceDownloader:
    """Headless fake used to drive one download job to completion."""

    def download_model(
        self,
        repo_id,
        local_dir,
        model_type,
        include_patterns,
        progress_callback,
        cancel_callback,
    ):
        del repo_id, model_type, include_patterns, cancel_callback
        progress_callback("config.json", 5, 10)
        progress_callback("config.json", 10, 10)
        return Path(local_dir)

    def download_file(
        self,
        repo_id,
        filename,
        local_dir,
        revision="main",
        progress_callback=None,
        cancel_callback=None,
    ):
        del repo_id, revision, cancel_callback
        if progress_callback is not None:
            progress_callback(5, 10)
            progress_callback(10, 10)
        return Path(local_dir) / filename


def _fresh_tracker() -> JobTracker:
    """Return a cleared shared tracker instance for one test."""
    tracker = JobTracker()
    tracker._jobs.clear()
    tracker._futures.clear()
    return tracker


def test_huggingface_job_service_completes_download(monkeypatch, tmp_path) -> None:
    """HuggingFace jobs should complete through the shared tracker."""
    tracker = _fresh_tracker()
    service = job_service.DownloadJobService(
        tracker=tracker,
        huggingface_downloader=FakeHuggingFaceDownloader(),
    )
    request = job_service.HuggingFaceDownloadRequest(
        repo_id="example/model",
        model_type="llm",
        output_dir=str(tmp_path),
    )
    monkeypatch.setattr(
        job_service,
        "prepare_huggingface_download_request",
        lambda **_kwargs: request,
    )

    job_id = asyncio.run(
        service.start_huggingface_download("example/model")
    )
    result = asyncio.run(service.get_result(job_id, timeout=1.0))
    status = asyncio.run(service.get_status(job_id))

    assert result["provider"] == "huggingface"
    assert result["paths"] == [str(tmp_path)]
    assert status is not None
    assert status.status is JobStatus.COMPLETED
    assert status.progress == 100.0


def test_civitai_job_service_completes_download(monkeypatch, tmp_path) -> None:
    """CivitAI jobs should share the same completion lifecycle."""
    tracker = _fresh_tracker()
    service = job_service.DownloadJobService(tracker=tracker)

    def fake_download_civitai_file(
        *_args,
        progress_callback=None,
        **_kwargs,
    ) -> bool:
        if progress_callback is not None:
            progress_callback(1024, 1024)
        return True

    monkeypatch.setattr(
        job_service,
        "fetch_model_info_for_url",
        lambda _url, _api_key: {
            "name": "Example Model",
            "selectedVersion": {
                "files": [
                    {
                        "name": "model.safetensors",
                        "downloadUrl": "https://example.com/model",
                        "sizeKB": 1,
                    }
                ]
            },
        },
    )
    monkeypatch.setattr(
        job_service,
        "download_civitai_file",
        fake_download_civitai_file,
    )

    job_id = asyncio.run(
        service.start_civitai_model_download(
            "https://civitai.com/models/123/example",
            output_dir=str(tmp_path),
        )
    )
    result = asyncio.run(service.get_result(job_id, timeout=1.0))

    assert result["provider"] == "civitai"
    assert result["model_name"] == "Example_Model"
    assert result["paths"] == [
        str(tmp_path / "Example_Model" / "model.safetensors")
    ]


def test_huggingface_file_job_service_downloads_single_file(tmp_path) -> None:
    """Single-file HF jobs should reuse the shared job lifecycle."""
    tracker = _fresh_tracker()
    service = job_service.DownloadJobService(
        tracker=tracker,
        huggingface_downloader=FakeHuggingFaceDownloader(),
    )

    job_id = asyncio.run(
        service.start_huggingface_file_download(
            "example/model",
            "model.bin",
            output_dir=str(tmp_path),
        )
    )
    result = asyncio.run(service.get_result(job_id, timeout=1.0))

    assert result["provider"] == "huggingface"
    assert result["filename"] == "model.bin"
    assert result["paths"] == [str(tmp_path / "model.bin")]


def test_huggingface_downloader_honors_cancel_callback(
    monkeypatch,
    tmp_path,
) -> None:
    """The service-owned HF downloader should remove partial files on cancel."""
    response = FakeResponse(
        headers={"content-length": "6"},
        chunks=[b"abc", b"def"],
    )
    target_dir = tmp_path / "downloads"
    cancellation_checks = iter([False, True])

    monkeypatch.setattr(
        model_downloader.requests,
        "get",
        lambda *args, **kwargs: response,
    )
    monkeypatch.setattr(model_downloader, "get_setting", lambda *args, **kwargs: "")

    downloader = model_downloader.HuggingFaceDownloader(cache_dir=str(tmp_path))

    with pytest.raises(model_downloader.DownloadCancelledError):
        downloader.download_file(
            "example/model",
            "model.bin",
            str(target_dir),
            cancel_callback=lambda: next(cancellation_checks),
        )

    assert not (target_dir / "model.bin").exists()


def test_url_job_service_extracts_archive(monkeypatch, tmp_path) -> None:
    """Generic URL jobs should support ZIP extraction for OpenVoice."""
    tracker = _fresh_tracker()
    service = job_service.DownloadJobService(tracker=tracker)
    source_archive = tmp_path / "source.zip"
    output_dir = tmp_path / "openvoice"

    with zipfile.ZipFile(source_archive, "w") as archive:
        archive.writestr("config.json", "{}")

    def fake_download_civitai_file(
        _url,
        output_path,
        _size,
        progress_callback=None,
        cancel_callback=None,
    ) -> bool:
        del cancel_callback
        output_path.write_bytes(source_archive.read_bytes())
        if progress_callback is not None:
            progress_callback(1024, 1024)
        return True

    monkeypatch.setattr(
        job_service,
        "download_civitai_file",
        fake_download_civitai_file,
    )

    job_id = asyncio.run(
        service.start_url_download(
            "https://example.com/openvoice.zip",
            output_dir=str(output_dir),
            extract_zip=True,
        )
    )
    result = asyncio.run(service.get_result(job_id, timeout=1.0))

    assert result["provider"] == "url"
    assert result["paths"] == [str(output_dir)]
    assert (output_dir / "config.json").exists()