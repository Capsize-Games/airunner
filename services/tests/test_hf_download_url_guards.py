"""Regression tests: HF downloads must reject redirect/off-host fetches.

The Civitai path validates every redirect hop against the SSRF policy;
the HuggingFace paths must do the same: a redirect to an off-host or
loopback URL must be refused, and a revision containing traversal must
never become a fetch.
"""

from __future__ import annotations

import logging
import threading

import pytest
import requests

from airunner_common import settings as airunner_common_settings
from airunner_services.downloads.civitai import _get_streaming_response
from airunner_services.downloads.huggingface_download_worker import (
    HuggingFaceDownloadWorker,
)
from airunner_services.llm.utils.model_downloader import HuggingFaceDownloader
from airunner_services.url_safety import SSRFBlocked


@pytest.fixture(autouse=True)
def _online_mode(monkeypatch):
    """Exercise SSRF validation itself, not the offline-mode short-circuit."""
    monkeypatch.setattr(airunner_common_settings, "AIRUNNER_OFFLINE_MODE", False)


def _make_worker() -> HuggingFaceDownloadWorker:
    worker = HuggingFaceDownloadWorker.__new__(HuggingFaceDownloadWorker)
    worker.logger = logging.getLogger("test-hf-url-guards")
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


class _OffHostStream:
    """A response whose final URL is off the HF host (redirect followed)."""

    status_code = 200
    headers = {"content-length": "4"}

    def __init__(self, url: str) -> None:
        self.url = url

    def raise_for_status(self) -> None:
        return None

    def iter_content(self, chunk_size: int = 8192):
        yield b"evil"

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


# --- Civitai hop validation (already-fixed pattern these tests pin) --------


def test_civitai_redirect_to_loopback_rejected(monkeypatch) -> None:
    """The guarded path refuses a redirect onto loopback (anchor: PASS)."""
    calls: list[str] = []

    class _Redirect:
        status_code = 302
        headers = {"location": "http://127.0.0.1:9/payload"}

        def close(self) -> None:
            return None

    def _fake_get(url, **kwargs):
        calls.append(url)
        return _Redirect()

    monkeypatch.setattr(requests, "get", _fake_get)
    with pytest.raises(SSRFBlocked):
        _get_streaming_response("http://93.184.216.1/file.bin", api_key="")
    assert calls, "no request was even attempted"


# --- HuggingFace downloader guards ------------------------------------------


def test_hf_downloader_rejects_traversal_revision(tmp_path, monkeypatch) -> None:
    """A revision with ``..`` must be rejected before any HTTP request."""
    requested: list[str] = []

    def _fail_on_call(url, **kwargs):
        requested.append(str(url))
        raise AssertionError("fetch must not happen for a bad revision")

    monkeypatch.setattr(requests, "get", _fail_on_call)
    downloader = HuggingFaceDownloader(cache_dir=str(tmp_path / "cache"))

    with pytest.raises(ValueError, match="(?i)revision|travers|invalid|not allowed"):
        downloader.download_file(
            repo_id="org/model",
            filename="weights.bin",
            local_dir=str(tmp_path / "model"),
            revision="../../evil",
        )
    assert requested == []


def test_hf_downloader_rejects_offhost_final_url(tmp_path, monkeypatch) -> None:
    """Content served from a private-network host must not be written."""
    monkeypatch.setattr(
        requests,
        "get",
        lambda url, **kwargs: _OffHostStream("http://10.0.0.5/payload"),
    )
    downloader = HuggingFaceDownloader(cache_dir=str(tmp_path / "cache"))

    # The legacy downloader wraps fetch failures in RuntimeError, but the
    # SSRF reason is preserved in the message and nothing is written.
    with pytest.raises((SSRFBlocked, ValueError, RuntimeError)):
        downloader.download_file(
            repo_id="org/model",
            filename="weights.bin",
            local_dir=str(tmp_path / "model"),
            revision="main",
        )
    assert not (tmp_path / "model" / "weights.bin").exists()


def _run_worker_expecting_failure(worker, **kwargs) -> None:
    """Run one worker download; assert it fails loudly without writing.

    The threaded worker reports failures through its signal channel
    (fail signal or error log message) rather than raising, so the test
    records emissions and requires both a loud failure and no file.
    """
    import re

    emitted: list = []
    worker.emit_signal = lambda *args, **kwargs: emitted.append((args, kwargs))  # noqa: E731
    worker._download_file(**kwargs)
    texts: list[str] = []
    for args, kw in emitted:
        for part in list(args) + list(kw.values()):
            if isinstance(part, dict):
                texts.extend(str(v) for v in part.values())
            else:
                texts.append(str(part))
    assert any(
        re.search(r"(?i)error|fail|refus|block|✗", text) for text in texts
    ), "expected a loud failure signal, none was emitted"
    assert not (kwargs["model_path"] / "weights.bin").exists()


def test_hf_worker_rejects_offhost_redirect(tmp_path, monkeypatch) -> None:
    """The threaded worker must refuse a redirect to a private host."""
    monkeypatch.setattr(requests, "head", lambda *a, **k: _FakeHead())
    monkeypatch.setattr(
        requests,
        "get",
        lambda *a, **k: _OffHostStream("http://10.0.0.5/payload"),
    )
    worker = _make_worker()
    model_path = tmp_path / "model"
    temp_dir = model_path / ".tmp"
    model_path.mkdir(parents=True)
    temp_dir.mkdir(parents=True)

    _run_worker_expecting_failure(
        worker,
        repo_id="org/model",
        filename="weights.bin",
        file_size=4,
        temp_dir=temp_dir,
        model_path=model_path,
        api_key="",
        revision="main",
    )


def test_hf_worker_rejects_redirect_to_loopback(tmp_path, monkeypatch) -> None:
    """A redirect onto loopback must be refused, not fetched."""
    monkeypatch.setattr(requests, "head", lambda *a, **k: _FakeHead())
    monkeypatch.setattr(
        requests,
        "get",
        lambda *a, **k: _OffHostStream("http://127.0.0.1:9/payload"),
    )
    worker = _make_worker()
    model_path = tmp_path / "model"
    temp_dir = model_path / ".tmp"
    model_path.mkdir(parents=True)
    temp_dir.mkdir(parents=True)

    _run_worker_expecting_failure(
        worker,
        repo_id="org/model",
        filename="weights.bin",
        file_size=4,
        temp_dir=temp_dir,
        model_path=model_path,
        api_key="",
        revision="main",
    )
