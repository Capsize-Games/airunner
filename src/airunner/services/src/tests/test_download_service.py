"""Tests for service-owned download coordination helpers."""

from pathlib import Path

from airunner_services.downloads import civitai
from airunner_services.downloads import huggingface
from airunner_services.downloads import service


class FakeResponse:
    """Minimal requests response double for download helper tests."""

    def __init__(self, status_code=200, headers=None, chunks=None):
        self.status_code = status_code
        self.headers = headers or {}
        self._chunks = chunks or []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def close(self) -> None:
        """Mirror the requests response close hook."""
        return None

    def raise_for_status(self) -> None:
        """Raise one HTTPError when the fake response is unsuccessful."""
        if self.status_code >= 400:
            raise __import__("requests").HTTPError(response=self)

    def iter_content(self, chunk_size=8192):
        """Yield the configured response payload chunks."""
        del chunk_size
        for chunk in self._chunks:
            yield chunk


def test_prepare_huggingface_download_request_prefers_gguf(monkeypatch):
    """GGUF-capable local targets should normalize onto one shared payload."""
    monkeypatch.setattr(
        huggingface.LLMProviderConfig,
        "resolve_download_target",
        lambda *args, **kwargs: {
            "model_type": "gguf",
            "repo_id": "bartowski/example-GGUF",
            "gguf_filename": "example-q4.gguf",
            "model_id": "example/model",
        },
    )
    monkeypatch.setattr(
        huggingface.LLMProviderConfig,
        "get_local_storage_path",
        lambda *args, **kwargs: "/tmp/gguf-models",
    )

    request = huggingface.prepare_huggingface_download_request(
        repo_id="example/model",
        model_type="llm",
    )

    assert request.repo_id == "bartowski/example-GGUF"
    assert request.model_type == "gguf"
    assert request.gguf_filename == "example-q4.gguf"
    assert request.output_dir == "/tmp/gguf-models"


def test_prepare_huggingface_download_request_honors_full_download(
    monkeypatch,
):
    """Full downloads should not force GGUF repo resolution."""
    calls = []

    def _resolve_download_target(*args, **kwargs):
        calls.append(kwargs)
        return {
            "model_type": "transformers",
            "repo_id": "example/full-model",
            "model_id": "example/model",
        }

    monkeypatch.setattr(
        huggingface.LLMProviderConfig,
        "resolve_download_target",
        _resolve_download_target,
    )
    monkeypatch.setattr(
        huggingface.LLMProviderConfig,
        "get_local_storage_path",
        lambda *args, **kwargs: "/tmp/full-models",
    )

    request = huggingface.prepare_huggingface_download_request(
        repo_id="example/model",
        model_type="llm",
        prefer_pre_quantized=False,
    )

    assert calls[0]["prefer_pre_quantized"] is False
    assert request.model_type == "llm"
    assert request.repo_id == "example/full-model"
    assert request.gguf_filename is None
    assert request.output_dir == "/tmp/full-models"


def test_fetch_civitai_model_info_attaches_selected_version(monkeypatch):
    """CivitAI fetches should preserve the requested version selection."""
    monkeypatch.setattr(
        civitai,
        "fetch_model_info",
        lambda model_id, api_key="": {
            "id": model_id,
            "modelVersions": [
                {"id": 1, "name": "old"},
                {"id": 22, "name": "selected"},
            ],
        },
    )

    data = service.fetch_civitai_model_info(
        "https://civitai.com/models/995002/example?modelVersionId=22"
    )

    assert data["selectedVersion"]["id"] == 22


def test_download_civitai_file_reports_progress(monkeypatch, tmp_path):
    """The shared CivitAI download helper should stream bytes and progress."""
    response = FakeResponse(
        headers={"content-length": "6"},
        chunks=[b"abc", b"def"],
    )
    progress_updates = []
    target_path = Path(tmp_path) / "model.bin"

    monkeypatch.setattr(civitai.requests, "get", lambda *args, **kwargs: response)

    completed = service.download_civitai_file(
        "https://example.com/model.bin",
        target_path,
        0,
        progress_callback=lambda current, total: progress_updates.append(
            (current, total)
        ),
    )

    assert completed is True
    assert target_path.read_bytes() == b"abcdef"
    assert progress_updates[-1] == (6, 6)


def test_provider_disabled_message_uses_provider_label():
    """Provider warnings should use the shared service-owned copy."""
    message = service.provider_disabled_message("huggingface")

    assert "HuggingFace downloads are disabled" in message