"""GET /api/v1/llm/models reports proven-loaded, not configured.

The ``loaded`` flag must use the same READY-plus-metadata proof
as the local-inference capability payload: a configured selection
with a stopped (or missing) runtime, or a READY runtime whose
health names no served model, reports ``loaded=false``. Hermetic:
stubbed settings, model registry, and runtime; no model, network,
GPU, or database access.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, Iterable, Optional

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import airunner_services.api.routes.llm_model_routes as model_routes
from airunner_services.runtimes.base import RuntimeClient
from airunner_services.runtimes.contracts import (
    RuntimeDescriptor,
    RuntimeHealth,
    RuntimeHealthStatus,
    RuntimeKind,
    RuntimeMode,
    TransportKind,
)
from airunner_services.runtimes.registry import (
    DEFAULT_PROVIDER,
    RuntimeRegistry,
    RuntimeRoute,
)

_CONFIGURED_ID = "gpt-oss-20b"
_OTHER_ID = "qwen3.5-9b"


class _FakeRuntimeClient(RuntimeClient):
    """Local runtime with canned health; no model or network."""

    def __init__(
        self,
        status: RuntimeHealthStatus,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.descriptor = RuntimeDescriptor(
            runtime=RuntimeKind.LLM,
            provider=DEFAULT_PROVIDER,
            mode=RuntimeMode.LOCAL_FALLBACK,
            transport=TransportKind.IN_PROCESS,
            supports_streaming=True,
        )
        self._status = status
        self._metadata = metadata or {}

    def invoke(self, request: Any) -> Any:
        del request
        raise AssertionError("/models must not invoke inference")

    def stream(self, request: Any) -> Iterable[Any]:
        del request
        raise AssertionError("/models must not stream inference")

    def healthcheck(self) -> RuntimeHealth:
        return RuntimeHealth(
            descriptor=self.descriptor,
            status=self._status,
            metadata=self._metadata,
        )


class _SettingsObjects:
    """Settings manager stub returning one configured selection."""

    def first(self) -> SimpleNamespace:
        return SimpleNamespace(
            model_id=_CONFIGURED_ID, model_version=None, model_path=None
        )


class _SettingsStub:
    """Stand-in for LLMGeneratorSettings (objects.first only)."""

    objects = _SettingsObjects()


def _spec(name: str) -> SimpleNamespace:
    """Return one fake LLM model spec for the registry stub."""
    return SimpleNamespace(
        name=name, size_mb=1024, model_type=SimpleNamespace(value="llm")
    )


class _RegistryStub:
    """Stand-in for ModelRegistry with two LLM models."""

    def __init__(self) -> None:
        self.models: Dict[str, SimpleNamespace] = {
            _CONFIGURED_ID: _spec("GPT-OSS 20B"),
            _OTHER_ID: _spec("Qwen 3.5 9B"),
        }


def _registry_with(client: RuntimeClient) -> RuntimeRegistry:
    registry = RuntimeRegistry()
    registry.register(
        RuntimeRoute(RuntimeKind.LLM, provider=DEFAULT_PROVIDER), client
    )
    return registry


def _client(
    monkeypatch: pytest.MonkeyPatch,
    registry: Optional[RuntimeRegistry],
) -> TestClient:
    monkeypatch.setattr(model_routes, "LLMGeneratorSettings", _SettingsStub)
    monkeypatch.setattr(model_routes, "ModelRegistry", _RegistryStub)
    app = FastAPI()
    app.include_router(model_routes.router, prefix="/api/v1/llm")
    if registry is not None:
        app.state.runtime_registry = registry
    return TestClient(app)


def test_stopped_runtime_reports_configured_model_not_loaded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Configured + STOPPED runtime: /models loaded stays false."""
    stopped = _FakeRuntimeClient(status=RuntimeHealthStatus.STOPPED)
    client = _client(monkeypatch, _registry_with(stopped))
    response = client.get("/api/v1/llm/models")
    assert response.status_code == 200
    body = response.json()
    entry = next(m for m in body if m["id"] == _CONFIGURED_ID)
    assert entry["loaded"] is False
    assert not any(m["loaded"] for m in body)


def test_ready_runtime_reports_configured_model_loaded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """READY plus served-model metadata: only that model loads."""
    ready = _FakeRuntimeClient(
        status=RuntimeHealthStatus.READY,
        metadata={"model_id": _CONFIGURED_ID},
    )
    client = _client(monkeypatch, _registry_with(ready))
    body = client.get("/api/v1/llm/models").json()
    loaded = [m["id"] for m in body if m["loaded"]]
    assert loaded == [_CONFIGURED_ID]
    entry = next(m for m in body if m["id"] == _CONFIGURED_ID)
    assert set(entry) == {"id", "name", "loaded", "size_mb"}
    assert entry["name"] == "GPT-OSS 20B"
    assert entry["size_mb"] == 1024


def test_ready_without_metadata_reports_nothing_loaded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """READY with no served-model metadata claims no load."""
    ready = _FakeRuntimeClient(status=RuntimeHealthStatus.READY)
    client = _client(monkeypatch, _registry_with(ready))
    body = client.get("/api/v1/llm/models").json()
    assert not any(m["loaded"] for m in body)


def test_no_runtime_registry_still_answers_not_loaded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing registry: /models still answers, nothing loaded."""
    response = _client(monkeypatch, None).get("/api/v1/llm/models")
    assert response.status_code == 200
    assert not any(m["loaded"] for m in response.json())
