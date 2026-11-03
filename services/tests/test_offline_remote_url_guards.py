"""Deterministic guards for remote vision, Ollama and legacy URL entry points.

All network-capable paths are replaced with local fakes. These tests prove the
application policy runs before transport and enforce URL/response-size limits;
they do not call providers, load models or contact external services.
"""

from __future__ import annotations

import asyncio
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from airunner_common import settings as common_settings
from airunner_services.llm.adapters.chat_model_factory_helpers import (
    build_provider_runtime_config,
)
from airunner_services.url_safety import OfflineModeBlocked, SSRFBlocked


class _FakeResponse:
    def __init__(self, body: bytes = b"", *, status_code: int = 200, headers=None):
        self.status_code = status_code
        self.headers = headers or {}
        self.encoding = "utf-8"
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def iter_content(self, chunk_size: int):
        del chunk_size
        yield self._body


class _FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


def _ollama_settings(base_url: str):
    return SimpleNamespace(
        use_local_llm=False,
        use_openrouter=False,
        use_ollama=True,
        use_openai=False,
        ollama_base_url=base_url,
        ollama_model="fixture-model",
    )


def test_remote_vision_url_rejects_offline_before_transport(monkeypatch) -> None:
    from airunner_services.llm.adapters.mixins import generation_vision_image_loading

    monkeypatch.setattr(common_settings, "AIRUNNER_OFFLINE_MODE", True)
    get = Mock(side_effect=AssertionError("transport must not run offline"))
    monkeypatch.setattr("requests.Session.get", get)
    adapter = SimpleNamespace(logger=Mock())

    assert generation_vision_image_loading.image_from_remote_url(
        adapter, "https://images.example.invalid/fixture.png"
    ) is None
    get.assert_not_called()


def test_remote_vision_private_redirect_is_rejected_before_second_request(
    monkeypatch,
) -> None:
    from airunner_services.llm.adapters.mixins import generation_vision_image_loading

    monkeypatch.setattr(common_settings, "AIRUNNER_OFFLINE_MODE", False)
    session = _FakeSession([
        _FakeResponse(
            status_code=302,
            headers={"location": "http://169.254.169.254/latest/meta-data/"},
        )
    ])
    monkeypatch.setattr("requests.Session", lambda: session)
    adapter = SimpleNamespace(logger=Mock())

    assert generation_vision_image_loading.image_from_remote_url(
        adapter, "http://93.184.216.34/fixture.png"
    ) is None
    assert len(session.calls) == 1
    assert session.calls[0][1]["allow_redirects"] is False


def test_remote_vision_response_size_is_bounded(monkeypatch) -> None:
    from airunner_services.llm.adapters.mixins import generation_vision_image_loading

    monkeypatch.setattr(common_settings, "AIRUNNER_OFFLINE_MODE", False)
    monkeypatch.setenv("AIRUNNER_SSRF_ALLOWED_HOSTS", "127.0.0.1")
    monkeypatch.setattr(generation_vision_image_loading, "MAX_REMOTE_IMAGE_BYTES", 4)
    session = _FakeSession([_FakeResponse(body=b"12345")])
    monkeypatch.setattr("requests.Session", lambda: session)
    adapter = SimpleNamespace(logger=Mock())

    assert generation_vision_image_loading.image_from_remote_url(
        adapter, "http://127.0.0.1/fixture.png"
    ) is None
    assert len(session.calls) == 1
    assert session.calls[0][1]["headers"] == {"User-Agent": "Mozilla/5.0"}


@pytest.mark.parametrize(
    "base_url",
    [
        "http://localhost:11434",
        "http://127.0.0.1:11434",
        "http://[::1]:11434",
    ],
)
def test_local_ollama_loopback_remains_available_offline(
    base_url: str, monkeypatch
) -> None:
    monkeypatch.setattr(common_settings, "AIRUNNER_OFFLINE_MODE", True)

    runtime = build_provider_runtime_config(_ollama_settings(base_url), None)

    assert runtime.provider == "ollama"
    assert runtime.base_url == base_url


def test_configured_remote_ollama_is_blocked_offline_before_dns(
    monkeypatch,
) -> None:
    from airunner_services import url_safety

    monkeypatch.setattr(common_settings, "AIRUNNER_OFFLINE_MODE", True)
    resolve = Mock(side_effect=AssertionError("offline policy must precede DNS"))
    monkeypatch.setattr(url_safety, "_resolve_host_ips", resolve)

    with pytest.raises(OfflineModeBlocked):
        build_provider_runtime_config(
            _ollama_settings("https://ollama.example.invalid:11434"), None
        )
    resolve.assert_not_called()


def test_private_ollama_requires_existing_explicit_host_allowlist(monkeypatch) -> None:
    from airunner_services.llm.adapters.chat_model_factory_helpers import (
        validate_ollama_base_url,
    )

    monkeypatch.setattr(common_settings, "AIRUNNER_OFFLINE_MODE", False)
    with pytest.raises(SSRFBlocked):
        validate_ollama_base_url("http://10.20.0.8:11434")

    monkeypatch.setenv("AIRUNNER_SSRF_ALLOWED_HOSTS", "10.20.0.8")
    assert validate_ollama_base_url("http://10.20.0.8:11434") == (
        "http://10.20.0.8:11434"
    )


def test_ollama_rejects_non_http_and_userinfo_urls(monkeypatch) -> None:
    from airunner_services.llm.adapters.chat_model_factory_helpers import (
        validate_ollama_base_url,
    )

    monkeypatch.setattr(common_settings, "AIRUNNER_OFFLINE_MODE", False)
    for base_url in (
        "file:///tmp/ollama.sock",
        "http://user:pass@ollama.example.invalid:11434",
    ):
        with pytest.raises(SSRFBlocked):
            validate_ollama_base_url(base_url)


def test_direct_ollama_constructor_preserves_local_loopback_offline(
    monkeypatch,
) -> None:
    import sys

    from airunner_services.llm.adapters.chat_model_factory_model_builders import (
        create_ollama_model,
    )

    monkeypatch.setattr(common_settings, "AIRUNNER_OFFLINE_MODE", True)
    monkeypatch.setitem(
        sys.modules,
        "langchain_ollama",
        SimpleNamespace(ChatOllama=lambda **kwargs: kwargs),
    )

    model = create_ollama_model("fixture-model")

    assert model == {
        "model": "fixture-model",
        "base_url": "http://localhost:11434",
        "temperature": 0.7,
    }


def test_direct_ollama_constructor_checks_remote_url_before_client_import(
    monkeypatch,
) -> None:
    from airunner_services.llm.adapters.chat_model_factory_model_builders import (
        create_ollama_model,
    )

    monkeypatch.setattr(common_settings, "AIRUNNER_OFFLINE_MODE", True)
    with pytest.raises(OfflineModeBlocked):
        create_ollama_model("fixture-model", "https://ollama.example.invalid")


def test_legacy_civitai_download_failure_preserves_existing_destination(
    tmp_path, monkeypatch, capsys
) -> None:
    from requests import RequestException

    from airunner_services.bin import airunner_civitai_download
    from airunner_services.downloads import service

    destination = tmp_path / "existing-model.bin"
    destination.write_bytes(b"previous-valid-file")
    monkeypatch.setattr(airunner_civitai_download, "tqdm", lambda **_kwargs: nullcontext())
    monkeypatch.setattr(service, "require_provider_allowed", lambda _name: None)
    monkeypatch.setattr(
        service,
        "download_civitai_file",
        Mock(side_effect=RequestException("token=private-fixture-secret")),
    )

    assert not airunner_civitai_download.download_file(
        "https://127.0.0.1/file", destination, 10, api_key="private-fixture-secret"
    )
    assert destination.read_bytes() == b"previous-valid-file"
    assert "private-fixture-secret" not in capsys.readouterr().out


def test_arxiv_exported_search_rejects_offline_before_client_io(monkeypatch) -> None:
    from airunner_services.tools.search_providers.arxiv_provider import ArxivProvider

    monkeypatch.setattr(common_settings, "AIRUNNER_OFFLINE_MODE", True)
    get = Mock(side_effect=AssertionError("arXiv transport must not run offline"))
    provider = ArxivProvider()
    create_client = AsyncMock(
        side_effect=AssertionError("offline check must precede client creation")
    )
    monkeypatch.setattr(provider, "get_async_client", create_client)

    results = asyncio.run(provider.search("fixture query", client=SimpleNamespace(get=get)))

    assert results == []
    create_client.assert_not_awaited()
    get.assert_not_called()


def test_legacy_civitai_helpers_apply_provider_policy_before_io(
    monkeypatch, tmp_path
) -> None:
    from airunner_services.bin import airunner_civitai_download as legacy
    from airunner_services.downloads.service import ProviderDownloadDisabled

    monkeypatch.setattr(common_settings, "AIRUNNER_OFFLINE_MODE", True)
    get = Mock(side_effect=AssertionError("CivitAI metadata must not fetch offline"))
    monkeypatch.setattr("requests.get", get)

    with pytest.raises(ProviderDownloadDisabled):
        legacy.fetch_model_info("1234")
    with pytest.raises(ProviderDownloadDisabled):
        legacy.download_file(
            "https://civitai.com/fixture.bin",
            tmp_path / "fixture.bin",
            4,
        )
    get.assert_not_called()


def test_legacy_civitai_download_delegates_to_shared_guarded_service(
    monkeypatch, tmp_path
) -> None:
    from airunner_services.bin import airunner_civitai_download as legacy
    from airunner_services.downloads import service

    monkeypatch.setattr(common_settings, "AIRUNNER_OFFLINE_MODE", False)
    monkeypatch.setitem(service._PROVIDER_CHECKS, "civitai", lambda: True)
    download = Mock(return_value=True)
    monkeypatch.setattr(service, "download_civitai_file", download)

    result = legacy.download_file(
        "https://civitai.com/fixture.bin",
        tmp_path / "fixture.bin",
        4,
        api_key="synthetic-token",
        chunk_size=2,
    )

    assert result is True
    download.assert_called_once()
    assert download.call_args.args == (
        "https://civitai.com/fixture.bin",
        tmp_path / "fixture.bin",
        4,
    )
    assert download.call_args.kwargs["api_key"] == "synthetic-token"
    assert download.call_args.kwargs["chunk_size"] == 2
    assert callable(download.call_args.kwargs["progress_callback"])
