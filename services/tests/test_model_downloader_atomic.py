"""Model downloads must not leave truncated files at the destination.

A stream that ends early used to leave a partial file behind, and the
next call then treated that file as a completed download.
"""

from __future__ import annotations

import pytest

from airunner_services.llm.utils import model_downloader as downloader_module


class _FakeResponse:
    url = "https://huggingface.co/repo/resolve/main/model.bin"
    status_code = 200
    headers = {"content-length": "100"}

    def raise_for_status(self) -> None:
        return None

    def iter_content(self, chunk_size: int = 8192):
        yield b"partial"


def test_truncated_download_leaves_no_destination_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        downloader_module.requests, "get", lambda *a, **k: _FakeResponse()
    )
    monkeypatch.setattr(
        "airunner_services.url_safety.validate_url_for_fetch",
        lambda url: None,
    )
    downloader = downloader_module.HuggingFaceDownloader.__new__(
        downloader_module.HuggingFaceDownloader
    )
    monkeypatch.setattr(
        downloader, "_get_huggingface_api_key", lambda: None, raising=False
    )

    with pytest.raises(RuntimeError, match="Failed to download"):
        downloader.download_file("org/repo", "model.bin", str(tmp_path))

    assert not (tmp_path / "model.bin").exists()
    assert not (tmp_path / "model.bin.part").exists()
