"""Unit tests for the CivitAI model-download extraction helpers.

_resolve_civitai_model, _download_civitai_files, and
_complete_civitai_job were extracted to keep _run_civitai_model_job
within the long-function threshold. These tests pin the version
resolution, the per-file abort semantics, and the completion
payload.
"""

import threading
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import airunner_services.downloads.job_service as job_mod
from airunner_services.downloads.job_service import DownloadJobService


def _make_service():
    service = DownloadJobService.__new__(DownloadJobService)
    service._tracker = MagicMock()
    service._cancel_job = MagicMock()
    service._complete_job = MagicMock()
    return service


def test_resolve_model_prefers_selected_version(monkeypatch):
    service = _make_service()
    monkeypatch.setattr(
        job_mod,
        "fetch_model_info_for_url",
        lambda url, key: {"name": "N", "selectedVersion": "v1"},
    )
    monkeypatch.setattr(
        job_mod,
        "get_files_to_download",
        lambda version, path: ["f1"] if version == "v1" else [],
    )
    monkeypatch.setattr(job_mod, "sanitize_filename", lambda name: name)
    name, path, files = service._resolve_civitai_model("u", "/out", "k")
    assert name == "N"
    assert str(path) == "/out/N"
    assert files == ["f1"]


def test_resolve_model_uses_select_version_fallback(monkeypatch):
    service = _make_service()
    monkeypatch.setattr(
        job_mod,
        "fetch_model_info_for_url",
        lambda url, key: {"name": "N"},
    )
    monkeypatch.setattr(
        job_mod, "select_version", lambda info: "v9"
    )
    monkeypatch.setattr(
        job_mod, "get_files_to_download", lambda version, path: []
    )
    monkeypatch.setattr(job_mod, "sanitize_filename", lambda name: name)
    _, _, files = service._resolve_civitai_model("u", "/out", "k")
    assert files == []


def test_resolve_model_raises_without_version(monkeypatch):
    service = _make_service()
    monkeypatch.setattr(
        job_mod, "fetch_model_info_for_url", lambda url, key: {}
    )
    monkeypatch.setattr(job_mod, "select_version", lambda info: None)
    with pytest.raises(ValueError, match="No CivitAI model version"):
        service._resolve_civitai_model("u", "/out", "k")


def test_download_success_collects_paths(monkeypatch):
    service = _make_service()
    monkeypatch.setattr(job_mod, "download_civitai_file", lambda *a, **k: True)
    monkeypatch.setattr(
        job_mod, "_assert_output_path_contained", lambda p: p
    )
    files = [{"url": "u1", "size": 5, "filename": "a.bin"}]
    paths = service._download_civitai_files(
        "j", threading.Event(), files, Path("/m"), 5, "k"
    )
    assert paths == ["/m/a.bin"]


def test_download_abort_cancels_and_returns_none(monkeypatch):
    service = _make_service()
    monkeypatch.setattr(job_mod, "download_civitai_file", lambda *a, **k: False)
    monkeypatch.setattr(
        job_mod, "_assert_output_path_contained", lambda p: p
    )
    files = [{"url": "u1", "size": 5, "filename": "a.bin"}]
    paths = service._download_civitai_files(
        "j", threading.Event(), files, Path("/m"), 5, "k"
    )
    assert paths is None
    service._cancel_job.assert_called_once_with("j")


def test_complete_job_payload():
    service = _make_service()
    service._complete_civitai_job("j", "url", "N", ["/m/a.bin"])
    service._complete_job.assert_called_once_with(
        "j",
        {
            "provider": "civitai",
            "url": "url",
            "model_name": "N",
            "paths": ["/m/a.bin"],
        },
    )
