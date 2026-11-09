"""Adversarial tests for the Muse art client (#2459)."""

from __future__ import annotations

import base64
from typing import Any

import pytest

from airunner_services.ipc.messages import RequestEnvelope
from airunner_services.runtimes.contracts import (
    RuntimeAction, RuntimeKind,
)
from airunner_services.runtimes.muse_art_client import MuseArtClient
from airunner_services.runtimes.muse_art_helpers import (
    MuseArtError, MuseArtSettings, fetch_url_image,
)
from airunner_services.runtimes.muse_usage import MuseUsageLedger

KEY = "sk-test-secret-value-123"


class _Resp:
    def __init__(self, payload: Any, status: int = 200) -> None:
        self._payload = payload
        self.status_code = status
        self.content = b"png-bytes"

    def json(self) -> Any:
        return self._payload


class _Session:
    def __init__(self, payload: Any) -> None:
        self._payload = payload
        self.posts: list[dict[str, Any]] = []
        self.gets: list[dict[str, Any]] = []

    def post(self, url: str, **kwargs: Any) -> _Resp:
        self.posts.append({"url": url, **kwargs})
        return _Resp(self._payload)

    def get(self, url: str, **kwargs: Any) -> _Resp:
        self.gets.append({"url": url, **kwargs})
        return _Resp(None)


def _client(session: _Session, **kwargs: Any) -> MuseArtClient:
    settings = MuseArtSettings(api_key=KEY, base_url="https://x/v1")
    return MuseArtClient(settings=settings, session=session, **kwargs)


def _envelope(prompt: str = "a cat", **over: Any) -> RequestEnvelope:
    payload: dict[str, Any] = {"prompt": prompt, "num_images": 1}
    payload.update(over)
    return RequestEnvelope(request_id="job-adv", runtime=RuntimeKind.ART,
        action=RuntimeAction.INVOKE, provider="muse", payload=payload)


def _b64() -> str:
    return base64.b64encode(b"img").decode("ascii")


@pytest.mark.parametrize("url", [
    "http://cdn.example.com/a.png",
    "https://127.0.0.1/a.png",
    "https://10.0.0.5/a.png",
    "https://192.168.1.9/a.png",
    "https://[::1]/a.png",
    "https://localhost/a.png",
    "https://169.254.1.1/a.png",
])
def test_image_url_ssrf_rejected(url: str) -> None:
    session = _Session(None)
    settings = MuseArtSettings(api_key=KEY)
    with pytest.raises(MuseArtError) as exc:
        fetch_url_image(session, url, settings)
    assert exc.value.code == "muse_invalid_image_url"
    assert session.gets == []


def test_public_https_url_fetched_without_redirects() -> None:
    session = _Session(None)
    settings = MuseArtSettings(api_key=KEY)
    out = fetch_url_image(session, "https://8.8.8.8/a.png",
        settings)
    assert base64.b64decode(out) == b"png-bytes"
    assert session.gets[0]["allow_redirects"] is False


def test_key_never_in_success_or_failure_surfaces() -> None:
    ok = _Session({"data": [{"b64_json": _b64()}]})
    resp = _client(ok).invoke(_envelope())
    assert KEY not in str(resp.model_dump())
    bad = _Session({"data": []})
    resp2 = _client(bad).invoke(_envelope())
    assert KEY not in str(resp2.model_dump())
    # The key's only legitimate place is the upstream auth header.
    assert KEY not in str(ok.posts[0]["json"])
    assert ok.posts[0]["headers"]["Authorization"] == f"Bearer {KEY}"


def test_usage_recorded_on_success_only() -> None:
    ledger = MuseUsageLedger()
    ok = _Session({"data": [{"b64_json": _b64()}]})
    _client(ok, ledger=ledger).invoke(_envelope())
    assert ledger.total_for("job-adv") == 1
    bad = _Session({"data": []})
    _client(bad, ledger=ledger).invoke(_envelope())
    assert ledger.total_for("job-adv") == 1


def test_per_job_limit_blocks_before_network() -> None:
    ledger = MuseUsageLedger(max_images_per_job=2)
    session = _Session({"data": [{"b64_json": _b64()}]})
    client = _client(session, ledger=ledger)
    resp = client.invoke(_envelope(num_images=5))
    assert resp.error is not None
    assert resp.error.code == "muse_quota_exceeded"
    assert session.posts == []


def test_local_model_path_rejected_for_muse() -> None:
    session = _Session({"data": [{"b64_json": _b64()}]})
    client = _client(session)
    with pytest.raises(ValueError, match="not a path"):
        client.invoke(_envelope(model="/models/Z-Image/model.safetensors"))
    assert session.posts == []


def test_hostname_resolving_private_rejected(monkeypatch: Any) -> None:
    import socket as socket_module
    monkeypatch.setattr(socket_module, "getaddrinfo",
        lambda *a, **k: [(2, 1, 6, "", ("10.1.2.3", 443))])
    session = _Session(None)
    settings = MuseArtSettings(api_key=KEY)
    with pytest.raises(MuseArtError) as exc:
        fetch_url_image(session, "https://images.example.net/a.png", settings)
    assert exc.value.code == "muse_invalid_image_url"
    assert session.gets == []


def test_hostname_resolving_public_allowed(monkeypatch: Any) -> None:
    import socket as socket_module
    monkeypatch.setattr(socket_module, "getaddrinfo",
        lambda *a, **k: [(2, 1, 6, "", ("8.8.4.4", 443))])
    session = _Session(None)
    settings = MuseArtSettings(api_key=KEY)
    out = fetch_url_image(session, "https://images.example.net/a.png", settings)
    assert base64.b64decode(out) == b"png-bytes"


def test_noncanonical_loopback_rejected(monkeypatch: Any) -> None:
    import socket as socket_module
    monkeypatch.setattr(socket_module, "getaddrinfo",
        lambda *a, **k: [(2, 1, 6, "", ("127.0.0.1", 443))])
    session = _Session(None)
    settings = MuseArtSettings(api_key=KEY)
    with pytest.raises(MuseArtError):
        fetch_url_image(session, "https://127.1/a.png", settings)


def test_excess_returned_images_rejected() -> None:
    payload = {"data": [{"b64_json": _b64()} for _ in range(5)]}
    session = _Session(payload)
    resp = _client(session).invoke(_envelope(num_images=2))
    assert resp.error is not None
    assert resp.error.code == "muse_too_many_images"


def test_settings_reject_bad_values() -> None:
    with pytest.raises(ValueError):
        MuseArtSettings.from_env({"MODEL_API_KEY": "x",
            "AIRUNNER_MUSE_TIMEOUT_S": "inf"})
    with pytest.raises(ValueError):
        MuseArtSettings.from_env({"MODEL_API_KEY": "x",
            "AIRUNNER_MUSE_BASE_URL": "http://169.254.169.254"})


def test_api_rejects_muse_incompatible_fields_early() -> None:
    from fastapi import HTTPException
    from airunner_services.api.routes.art_contracts import (
        GenerationRequest,
    )
    from airunner_services.api.routes.art_generation_start_routes import (
        _reject_muse_incompatible,
    )
    for over in ({"negative_prompt": "no"}, {"image_b64": "aW1n"},
                 {"version": "Z-Image Turbo"}, {"model": "/local/x"}):
        req = GenerationRequest(prompt="cat", provider="muse", **over)
        with pytest.raises(HTTPException) as exc:
            _reject_muse_incompatible(req)
        assert exc.value.status_code == 400
    ok = GenerationRequest(prompt="cat", provider="muse")
    _reject_muse_incompatible(ok)
    local = GenerationRequest(prompt="cat", negative_prompt="no")
    _reject_muse_incompatible(local)


def test_bootstrap_bad_muse_env_fails_closed(monkeypatch: Any) -> None:
    from airunner_services.runtimes.bootstrap import (
        _register_muse_art_client, muse_art_enabled,
    )
    from airunner_services.runtimes.registry import RuntimeRegistry
    monkeypatch.setenv("MODEL_API_KEY", "test-only")
    monkeypatch.setenv("AIRUNNER_MUSE_TIMEOUT_S", "not-a-number")
    assert muse_art_enabled()
    registry = RuntimeRegistry()
    _register_muse_art_client(registry)  # must not raise
    assert list(registry.list_routes()) == []
    monkeypatch.delenv("AIRUNNER_MUSE_TIMEOUT_S")
