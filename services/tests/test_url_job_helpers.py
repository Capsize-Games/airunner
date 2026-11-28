"""Unit tests for the URL download job extraction helpers.

_validate_url_job_target, _make_url_progress_reporter, and
_finalize_download_output were extracted to keep
_run_url_download_job within the long-function threshold. These
tests pin the validation triage, the progress throttle, and the
finalize paths.
"""

import threading
import zipfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from airunner_services.downloads.job_service import DownloadJobService


def _make_service():
    service = DownloadJobService.__new__(DownloadJobService)
    service._tracker = MagicMock()
    service._fail_job = MagicMock()
    service._forget_job = MagicMock()
    service._cancel_job = MagicMock()
    service._update_job = MagicMock()
    service._record_file_progress = MagicMock()
    service._record_log_message = MagicMock()
    return service


def test_validate_target_happy_path(tmp_path, monkeypatch):
    import airunner_services.downloads.job_service as job_mod

    monkeypatch.setattr(job_mod, "validate_url_for_fetch", lambda url: None)
    monkeypatch.setattr(
        job_mod, "_resolve_safe_output_dir", lambda d: tmp_path
    )
    monkeypatch.setattr(
        job_mod, "_assert_output_path_contained", lambda p: p
    )
    service = _make_service()
    target = service._validate_url_job_target(
        "j", "https://example.com/a", str(tmp_path), "f.bin"
    )
    assert target is not None
    root, path, name = target
    assert name == "f.bin"
    assert root.is_dir()


def test_validate_target_rejects_bad_filename(tmp_path, monkeypatch):
    import airunner_services.downloads.job_service as job_mod

    monkeypatch.setattr(job_mod, "validate_url_for_fetch", lambda url: None)
    monkeypatch.setattr(
        job_mod,
        "_safe_filename",
        MagicMock(side_effect=ValueError("bad name")),
    )
    service = _make_service()
    assert (
        service._validate_url_job_target(
            "j", "https://example.com/a", str(tmp_path), "bad"
        )
        is None
    )
    service._fail_job.assert_called_once()
    service._forget_job.assert_called_once()


def test_progress_reporter_throttles():
    service = _make_service()
    progress = service._make_url_progress_reporter("j", "f.bin")
    progress(50, 100)
    progress(505, 1000)
    assert service._record_file_progress.call_count == 1
    progress(100, 100)
    assert service._record_file_progress.call_count == 2
    service._update_job.assert_called()


def test_finalize_without_extract_returns_file_path(tmp_path):
    service = _make_service()
    out = tmp_path / "f.bin"
    out.write_bytes(b"x")
    paths = service._finalize_download_output(
        "j", tmp_path, out, str(tmp_path), "f.bin", False
    )
    assert paths == [str(out)]
    assert out.exists()


def test_finalize_with_extract_unzips_and_removes_archive(tmp_path):
    service = _make_service()
    archive_path = tmp_path / "a.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("inside.txt", "hello")
    paths = service._finalize_download_output(
        "j", tmp_path, archive_path, str(tmp_path), "a.zip", True
    )
    assert paths == [str(tmp_path)]
    assert (tmp_path / "inside.txt").exists()
    assert not archive_path.exists()
