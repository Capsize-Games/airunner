"""Regression tests: HF download path traversal must stay inside the model dir.

Covers the worker filename/revision ``../`` cases: a malicious or corrupt
upstream listing must never write outside the model directory, and a
revision containing path separators must be rejected before any fetch.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from airunner_common import settings as airunner_common_settings
from airunner_services.downloads.huggingface_download_worker import (
    HuggingFaceDownloadWorker,
)


@pytest.fixture(autouse=True)
def _online_mode(monkeypatch):
    """Exercise path validation itself, not the offline-mode short-circuit."""
    monkeypatch.setattr(airunner_common_settings, "AIRUNNER_OFFLINE_MODE", False)


def _make_worker() -> HuggingFaceDownloadWorker:
    """Return a worker without running its heavyweight ``__init__``."""
    worker = HuggingFaceDownloadWorker.__new__(HuggingFaceDownloadWorker)
    worker.logger = logging.getLogger("test-hf-traversal")
    worker._lock = threading.Lock()
    worker._completed_files = set()
    worker._failed_files = set()
    worker._file_progress = {}
    worker._file_sizes = {}
    worker._file_threads = {}
    worker._total_downloaded = 0
    worker._total_size = 0
    worker.is_cancelled = False
    worker._current_model_type = None
    worker._current_pipeline_action = None
    worker.emit_signal = lambda *a, **k: None  # noqa: E731
    worker._mark_file_complete = lambda name: worker._completed_files.add(name)  # noqa: E731
    worker._mark_file_failed = lambda name: worker._failed_files.add(name)  # noqa: E731
    return worker


class _FakeHead:
    headers: dict = {}

    def raise_for_status(self) -> None:
        return None


class _FakeStream:
    """Minimal streaming response double for ``requests.get``."""

    def __init__(self, payload: bytes = b"data-bytes") -> None:
        self.status_code = 200
        self.headers = {"content-length": str(len(payload))}
        self._payload = payload
        self.url = "https://huggingface.co/org/model/resolve/main/file"

    def raise_for_status(self) -> None:
        return None

    def iter_content(self, chunk_size: int = 8192):
        yield self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture()
def _no_network(monkeypatch):
    """Replace direct ``requests`` calls with in-memory fakes."""
    import requests

    monkeypatch.setattr(requests, "head", lambda *a, **k: _FakeHead())
    monkeypatch.setattr(requests, "get", lambda *a, **k: _FakeStream())
    return requests


def test_traversal_filename_stays_inside_model_dir(tmp_path, _no_network) -> None:
    """``../`` filenames must not escape the model directory."""
    worker = _make_worker()
    model_path = tmp_path / "model"
    temp_dir = tmp_path / "model" / ".tmp"
    model_path.mkdir(parents=True)
    temp_dir.mkdir(parents=True)

    with pytest.raises(ValueError, match="(?i)travers|outside|invalid|not allowed"):
        worker._download_file(
            repo_id="org/model",
            filename="../../evil.bin",
            file_size=10,
            temp_dir=temp_dir,
            model_path=model_path,
            api_key="",
            revision="main",
        )

    escaped = (model_path / "../../evil.bin").resolve()
    assert not escaped.exists(), f"traversal escaped model dir: {escaped}"


def test_absolute_filename_rejected(tmp_path, _no_network) -> None:
    """Absolute filenames must be rejected, not written to disk root."""
    worker = _make_worker()
    model_path = tmp_path / "model"
    temp_dir = tmp_path / "model" / ".tmp"
    model_path.mkdir(parents=True)
    temp_dir.mkdir(parents=True)

    with pytest.raises(ValueError, match="(?i)travers|outside|invalid|not allowed|absolute"):
        worker._download_file(
            repo_id="org/model",
            filename="/tmp/evil-absolute.bin",
            file_size=10,
            temp_dir=temp_dir,
            model_path=model_path,
            api_key="",
            revision="main",
        )


def test_revision_traversal_rejected_before_fetch(tmp_path, monkeypatch) -> None:
    """A revision containing ``..`` must be rejected before any HTTP call."""
    import requests

    worker = _make_worker()
    model_path = tmp_path / "model"
    temp_dir = tmp_path / "model" / ".tmp"
    model_path.mkdir(parents=True)
    temp_dir.mkdir(parents=True)

    requested: list[str] = []

    def _fail_on_call(*args, **kwargs):
        requested.append(str(args[0]) if args else "")
        raise AssertionError("network fetch must not happen for bad revision")

    monkeypatch.setattr(requests, "head", _fail_on_call)
    monkeypatch.setattr(requests, "get", _fail_on_call)

    with pytest.raises(ValueError, match="(?i)revision|travers|invalid|not allowed"):
        worker._download_file(
            repo_id="org/model",
            filename="weights.bin",
            file_size=10,
            temp_dir=temp_dir,
            model_path=model_path,
            api_key="",
            revision="../../evil",
        )
    assert requested == []


def test_nested_subdirectory_filename_still_downloads(tmp_path, _no_network) -> None:
    """Legit in-tree subpaths (e.g. ``scheduler/...``) must keep working."""
    worker = _make_worker()
    model_path = tmp_path / "model"
    temp_dir = tmp_path / "model" / ".tmp"
    model_path.mkdir(parents=True)
    temp_dir.mkdir(parents=True)

    worker._download_file(
        repo_id="org/model",
        filename="scheduler/scheduler_config.json",
        file_size=10,
        temp_dir=temp_dir,
        model_path=model_path,
        api_key="",
        revision="main",
    )

    final = (model_path / "scheduler" / "scheduler_config.json").resolve()
    assert final.is_file()
    assert model_path.resolve() in final.parents
