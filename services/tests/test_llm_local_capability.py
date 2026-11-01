"""Local-inference capability contract for Local Node consumers.

The payload must stay truthful against the real provider config
and routing matrix, and must answer (not 503) when no local LLM
runtime is registered, so another process can tell "daemon up,
model not loaded" apart from "daemon dead". No model, network,
GPU, or database access.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import airunner_services.api.routes.llm_local_routes as local_routes
from airunner_services.api.routes.llm_local_routes import router
from airunner_services.llm.companion.local_routing import (
    PIPELINE_ROUTES,
    CompanionPipeline,
)
from airunner_services.llm.local_capability import (
    CAPABILITY_CONTRACT,
    build_local_capability,
)
from airunner_services.llm.provider_config import LLMProviderConfig
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


class _FakeRuntimeClient(RuntimeClient):
    """Local runtime with canned health; no model or network."""

    def __init__(
        self,
        status: RuntimeHealthStatus = RuntimeHealthStatus.READY,
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
        raise AssertionError("capability must not invoke inference")

    def stream(self, request: Any) -> Iterable[Any]:
        del request
        raise AssertionError("capability must not stream inference")

    def healthcheck(self) -> RuntimeHealth:
        return RuntimeHealth(
            descriptor=self.descriptor,
            status=self._status,
            metadata=self._metadata,
        )


class _BrokenRuntimeClient(_FakeRuntimeClient):
    """Runtime whose healthcheck raises (crashed sidecar)."""

    def healthcheck(self) -> RuntimeHealth:
        raise RuntimeError("sidecar gone")


def _registry_with(client: RuntimeClient) -> RuntimeRegistry:
    registry = RuntimeRegistry()
    registry.register(
        RuntimeRoute(RuntimeKind.LLM, provider=DEFAULT_PROVIDER), client
    )
    return registry


def test_models_match_supported_local_provider_config() -> None:
    """Only supported local ids appear, with truthful GGUF data."""
    payload = build_local_capability()
    expected = LLMProviderConfig.get_models_for_provider("local")
    assert [m["id"] for m in payload["models"]] == expected
    by_id = {m["id"]: m for m in payload["models"]}
    qwen = by_id["qwen3.5-9b"]
    info = LLMProviderConfig.LOCAL_MODELS["qwen3.5-9b"]
    assert qwen["context_length"] == info["context_length"]
    assert qwen["vram_gb"]["4bit"] == info["vram_4bit_gb"]
    assert qwen["gguf"]["supported"] is True
    assert qwen["gguf"]["filename"] == info["gguf_filename"]
    profiles = {p["name"]: p["n_ctx"] for p in qwen["gguf_runtime_profiles"]}
    assert profiles["default"] == 32768
    assert by_id["custom"]["gguf"]["supported"] is False


def test_pipelines_cover_routing_matrix_and_stay_local() -> None:
    """Every companion pipeline is listed; embedding is local-only."""
    payload = build_local_capability()
    by_name = {p["pipeline"]: p for p in payload["pipelines"]}
    assert set(by_name) == {p.value for p in PIPELINE_ROUTES}
    assert set(by_name) == {p.value for p in CompanionPipeline}
    assert by_name["embedding"]["local_only"] is True
    assert by_name["embedding"]["runtime"] is None
    assert by_name["dialogue"]["runtime"] == "llm"
    assert by_name["dialogue"]["local_only"] is False
    assert payload["routing"]["remote_requires_consent"] is True
    assert payload["routing"]["remote_provider"] == "openrouter"


def test_runtime_unavailable_without_registry_or_route() -> None:
    """Missing runtime is reported, never raised or faked ready."""
    assert build_local_capability()["runtime"]["status"] == "unavailable"
    empty = build_local_capability(registry=RuntimeRegistry())
    assert empty["runtime"]["status"] == "unavailable"
    assert empty["runtime"]["descriptor"] is None


def test_runtime_health_and_loaded_flag_are_live() -> None:
    """READY health with served-model metadata proves the load."""
    serving = _FakeRuntimeClient(metadata={"model_id": "gpt-oss-20b"})
    payload = build_local_capability(
        registry=_registry_with(serving),
        configured_model_id="gpt-oss-20b",
    )
    assert payload["runtime"]["status"] == "ready"
    assert payload["runtime"]["descriptor"]["supports_streaming"] is True
    configured = [m["id"] for m in payload["models"] if m["configured"]]
    loaded = [m["id"] for m in payload["models"] if m["loaded"]]
    assert configured == loaded == ["gpt-oss-20b"]



def test_configured_model_is_not_loaded_without_ready_runtime() -> None:
    """A selection alone never claims a load (stopped daemon)."""
    for registry in (None, RuntimeRegistry()):
        payload = build_local_capability(
            registry=registry, configured_model_id="gpt-oss-20b"
        )
        configured = [m["id"] for m in payload["models"] if m["configured"]]
        assert configured == ["gpt-oss-20b"]
        assert not any(m["loaded"] for m in payload["models"])


def test_configured_model_is_not_loaded_when_runtime_stopped() -> None:
    """STOPPED health keeps configured true and loaded false."""
    stopped = _FakeRuntimeClient(status=RuntimeHealthStatus.STOPPED)
    payload = build_local_capability(
        registry=_registry_with(stopped),
        configured_model_id="gpt-oss-20b",
    )
    assert payload["runtime"]["status"] == "stopped"
    entry = next(m for m in payload["models"] if m["id"] == "gpt-oss-20b")
    assert entry["configured"] is True
    assert entry["loaded"] is False


def test_health_metadata_names_the_actually_served_model() -> None:
    """Served-model metadata wins over the configured selection."""
    serving = _FakeRuntimeClient(metadata={"model_id": "gpt-oss-20b"})
    payload = build_local_capability(
        registry=_registry_with(serving),
        configured_model_id="qwen3.5-9b",
    )
    configured = [m["id"] for m in payload["models"] if m["configured"]]
    loaded = [m["id"] for m in payload["models"] if m["loaded"]]
    assert configured == ["qwen3.5-9b"]
    assert loaded == ["gpt-oss-20b"]


def test_broken_healthcheck_reports_failed_not_exception() -> None:
    """A crashing healthcheck degrades the payload, not the call."""
    payload = build_local_capability(
        registry=_registry_with(_BrokenRuntimeClient()),
        configured_model_id="gpt-oss-20b",
    )
    assert payload["runtime"]["status"] == "failed"
    assert "sidecar gone" not in payload["runtime"]["details"]
    assert not any(m["loaded"] for m in payload["models"])


def _client(registry: RuntimeRegistry | None) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/llm")
    if registry is not None:
        app.state.runtime_registry = registry
    return TestClient(app)


def test_route_answers_200_without_any_runtime() -> None:
    """Daemon-up/model-down is a 200 capability answer, not 503."""
    response = _client(None).get("/api/v1/llm/local-inference")
    assert response.status_code == 200
    body = response.json()
    assert body["contract"] == CAPABILITY_CONTRACT
    assert body["contract_version"] == "1"
    assert body["runtime"]["status"] == "unavailable"
    assert body["endpoints"]["stream"] == "/api/v1/llm/stream"
    assert {m["id"] for m in body["models"]} >= {"qwen3.5-9b"}


def test_route_reports_ready_runtime_from_app_state() -> None:
    """The HTTP surface reflects the registry on app.state."""
    client = _client(_registry_with(_FakeRuntimeClient()))
    body = client.get("/api/v1/llm/local-inference").json()
    assert body["runtime"]["status"] == "ready"
    assert body["runtime"]["descriptor"]["transport"] == "in_process"


def test_route_configured_but_not_loaded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Configured selection with no runtime: loaded stays false."""
    monkeypatch.setattr(
        local_routes, "_configured_model_id", lambda: "gpt-oss-20b"
    )
    body = _client(None).get("/api/v1/llm/local-inference").json()
    assert body["runtime"]["status"] == "unavailable"
    entry = next(m for m in body["models"] if m["id"] == "gpt-oss-20b")
    assert entry["configured"] is True
    assert entry["loaded"] is False
    assert not any(m["loaded"] for m in body["models"])
