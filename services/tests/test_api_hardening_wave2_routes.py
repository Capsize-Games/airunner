"""Wave-2 API hardening: legacy admin/setup/batch/art/LLM clamps."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from airunner_services.api.routes import legacy_admin_routes
from airunner_services.api.routes.legacy_art_routes import (
    _resolve_legacy_art_params,
)
from airunner_services.api.routes.legacy_contracts import LegacyArtRequest
from airunner_services.api.routes.legacy_ollama_compat import (
    _ollama_chat_request,
    ollama_copy,
    ollama_create,
    ollama_embed,
    ollama_pull,
)
from airunner_services.api.routes.legacy_openai_compat import (
    _build_openai_request,
)
from airunner_services.api.routes.setup import _resolve_base_path
from airunner_services.api.server import create_app


class _FakeApp:
    """Minimal app surface for routes that never need a real LLM."""

    def __init__(self) -> None:
        self.llm = None

    def emit_signal(self, _code, _data=None) -> None:
        """Ignore signal emissions during validation tests."""


def _client(monkeypatch) -> TestClient:
    """Return a TestClient with auth disabled."""
    monkeypatch.setenv("AIRUNNER_API_KEY", "")
    monkeypatch.setenv("AIRUNNER_INSECURE_NO_AUTH", "1")
    return TestClient(
        create_app(
            allowed_origins=["http://localhost"],
            enable_cors=False,
            app_instance=_FakeApp(),
        )
    )


def test_admin_reset_endpoints_not_implemented(monkeypatch) -> None:
    """Fake-ok admin endpoints now report 501, never false success."""
    client = _client(monkeypatch)
    for path in ("/admin/reset_memory", "/admin/reset_database"):
        assert client.post(path).status_code == 501


def test_admin_shutdown_requires_admin_key(monkeypatch) -> None:
    """Shutdown is refused without the separate admin credential."""
    monkeypatch.setenv("AIRUNNER_ADMIN_KEY", "s3cret")
    client = _client(monkeypatch)
    assert client.post("/admin/shutdown").status_code == 403
    calls: list[bool] = []
    monkeypatch.setattr(
        legacy_admin_routes,
        "schedule_process_shutdown",
        lambda *a, **k: calls.append(True),
    )
    response = client.post(
        "/admin/shutdown", headers={"x-admin-key": "s3cret"}
    )
    assert response.status_code == 200
    assert calls == [True]


def test_setup_base_path_allowlist() -> None:
    """Install roots outside the data dir are rejected."""
    from airunner_common.settings import AIRUNNER_BASE_PATH

    assert _resolve_base_path(str(AIRUNNER_BASE_PATH))
    for raw in ("/etc", "/tmp/evil", str(AIRUNNER_BASE_PATH) + "/../x"):
        with pytest.raises(HTTPException):
            _resolve_base_path(raw)


def test_generate_batch_prompt_cap(monkeypatch) -> None:
    """More than 16 prompts per batch request is rejected."""
    client = _client(monkeypatch)
    response = client.post(
        "/llm/generate_batch", json={"prompts": ["x"] * 17}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "too_many_prompts"


def test_legacy_art_params_bounded() -> None:
    """Legacy art dims/steps/samples reject out-of-range values."""
    good = _resolve_legacy_art_params(LegacyArtRequest(prompt="x"))
    assert good["width"] == 1024
    for kwargs in (
        {"width": 99999},
        {"height": 1},
        {"steps": 1000},
        {"n_samples": 99},
        {"cfg_scale": 500.0},
    ):
        with pytest.raises(HTTPException):
            _resolve_legacy_art_params(
                LegacyArtRequest(prompt="x", **kwargs)
            )


def test_openai_sampling_clamped() -> None:
    """Wild OpenAI sampling params fall back to documented defaults."""
    request = _build_openai_request(
        {"temperature": 9.0, "max_tokens": -5}, "p", "", []
    )
    assert request.temperature == 0.7
    assert request.max_new_tokens == 2048
    request = _build_openai_request(
        {"temperature": 1.5, "max_tokens": 100}, "p", "", []
    )
    assert request.temperature == 1.5
    assert request.max_new_tokens == 100


def test_ollama_sampling_clamped() -> None:
    """Wild Ollama options fall back; mistyped fields are rejected."""
    request = _ollama_chat_request(
        {"temperature": -2.0, "num_predict": 10**9}, "", [], True, None
    )
    assert request.temperature == 0.7
    assert request.max_new_tokens == 2048
    assert request.enable_thinking is True
    with pytest.raises(HTTPException):
        _ollama_chat_request([], "", [], None, None)
    with pytest.raises(HTTPException):
        _ollama_chat_request({}, "", [], "yes", None)
    with pytest.raises(HTTPException):
        _ollama_chat_request({}, "", [], None, 42)


def test_ollama_embed_cap_and_model_mgmt_501() -> None:
    """Embed lists are capped; pull/copy/create report 501."""
    with pytest.raises(HTTPException):
        ollama_embed({"input": ["x"] * 65})
    for func in (ollama_pull, ollama_copy, ollama_create):
        with pytest.raises(HTTPException) as exc:
            func({})
        assert exc.value.status_code == 501
