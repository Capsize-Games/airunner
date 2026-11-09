"""Provider routing tests for art generation (issue #2453)."""

from __future__ import annotations

import asyncio
import sys
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from airunner_services.api.routes import art_generation_start_routes as start
from airunner_services.api.routes.art_contracts import GenerationRequest
from airunner_services.api.routes.art_job_requests import (
    build_art_envelope, build_generation_job_metadata,
)
from airunner_services.api.routes.art_runtime_registry import (
    art_runtime_route, resolve_art_client,
)
from airunner_services.runtimes.base import RuntimeClient
from airunner_services.runtimes.bootstrap import _register_muse_art_client
from airunner_services.runtimes.contracts import (
    RuntimeDescriptor, RuntimeHealth, RuntimeHealthStatus,
    RuntimeKind, RuntimeMode, TransportKind,
)
from airunner_services.runtimes.registry import RuntimeRegistry, RuntimeRoute


class _FakeClient(RuntimeClient):
    """Minimal runtime client registered under one route."""

    def __init__(self, provider: str, mode: RuntimeMode) -> None:
        self.descriptor = RuntimeDescriptor(
            runtime=RuntimeKind.ART,
            provider=provider,
            mode=mode,
            transport=TransportKind.IN_PROCESS,
        )

    def invoke(self, request: Any) -> Any:
        return request

    def healthcheck(self) -> RuntimeHealth:
        return RuntimeHealth(
            descriptor=self.descriptor, status=RuntimeHealthStatus.READY
        )


def _registry_with(*clients: _FakeClient) -> RuntimeRegistry:
    """Return a registry holding each client under its own route."""
    registry = RuntimeRegistry()
    for client in clients:
        route = RuntimeRoute(
            RuntimeKind.ART,
            provider=client.descriptor.provider,
            deployment_mode=client.descriptor.mode.value,
        )
        registry.register(route, client)
    return registry


def _local_client() -> _FakeClient:
    """Return the fake client matching the default local route."""
    route, _detail = art_runtime_route("local")
    mode = RuntimeMode(route.deployment_mode)
    return _FakeClient(route.provider, mode)


def test_request_provider_defaults_to_local() -> None:
    """Old callers without a provider keep local behaviour."""
    assert GenerationRequest(prompt="a cat").provider == "local"


def test_request_provider_accepts_muse() -> None:
    """An explicit muse provider is accepted."""
    request = GenerationRequest(prompt="a cat", provider="muse")
    assert request.provider == "muse"


def test_request_provider_rejects_unknown() -> None:
    """An unknown provider is rejected, never silently remapped."""
    with pytest.raises(ValidationError):
        GenerationRequest(prompt="a cat", provider="bogus")


def test_muse_route_is_cloud() -> None:
    """Muse resolves to the ART/muse/cloud route."""
    route, _detail = art_runtime_route("muse")
    assert RuntimeMode.CLOUD.value == "cloud"
    assert route.provider == "muse"
    assert route.deployment_mode == RuntimeMode.CLOUD.value


def test_resolve_local_default() -> None:
    """Default resolution returns the registered local client."""
    client = _local_client()
    registry = _registry_with(client)
    assert resolve_art_client(registry) is client


def test_resolve_muse_client() -> None:
    """Muse resolution returns the registered cloud client."""
    muse = _FakeClient("muse", RuntimeMode.CLOUD)
    registry = _registry_with(_local_client(), muse)
    assert resolve_art_client(registry, provider="muse") is muse


def test_resolve_absent_provider_is_503_no_fallback() -> None:
    """Missing/unknown providers are 503, never another client."""
    local_only = _registry_with(_local_client())
    muse_only = _registry_with(_FakeClient("muse", RuntimeMode.CLOUD))
    cases = [(local_only, "muse"), (muse_only, "local"), (local_only, "x")]
    for registry, provider in cases:
        with pytest.raises(HTTPException) as exc_info:
            resolve_art_client(registry, provider=provider)
        assert exc_info.value.status_code == 503


def test_envelope_and_metadata_carry_provider() -> None:
    """Envelope provider, envelope metadata, and job metadata agree."""
    request = GenerationRequest(prompt="a cat", provider="muse")
    envelope = build_art_envelope("job-1", request)
    assert envelope.provider == "muse"
    assert envelope.metadata == {"provider": "muse"}
    assert build_generation_job_metadata(request, 7)["provider"] == "muse"


def test_envelope_defaults_to_local_provider() -> None:
    """A provider-less request produces a local envelope."""
    envelope = build_art_envelope("job-1", GenerationRequest(prompt="x"))
    assert envelope.provider == "local"
    assert envelope.metadata == {"provider": "local"}


def _fake_muse_module(client: _FakeClient) -> ModuleType:
    """Return a stand-in muse client module yielding one client."""
    module = ModuleType("airunner_services.runtimes.muse_art_client")
    setattr(module, "MuseArtClient", lambda: client)
    return module


def test_bootstrap_skips_muse_without_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No MODEL_API_KEY means no muse route is registered."""
    muse = _FakeClient("muse", RuntimeMode.CLOUD)
    monkeypatch.setitem(
        sys.modules,
        "airunner_services.runtimes.muse_art_client",
        _fake_muse_module(muse),
    )
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    registry = RuntimeRegistry()
    _register_muse_art_client(registry)
    assert list(registry.list_routes()) == []


def test_bootstrap_registers_muse_with_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With MODEL_API_KEY the muse cloud route is registered."""
    muse = _FakeClient("muse", RuntimeMode.CLOUD)
    monkeypatch.setitem(
        sys.modules,
        "airunner_services.runtimes.muse_art_client",
        _fake_muse_module(muse),
    )
    monkeypatch.setenv("MODEL_API_KEY", "test-only-value")
    registry = RuntimeRegistry()
    _register_muse_art_client(registry)
    assert resolve_art_client(registry, provider="muse") is muse


class _FakeTracker:
    """JobTracker stand-in that never marks the job running."""

    def __init__(self) -> None:
        self.bound: Any = None

    async def create_art_job(self, metadata: Any, capacity: int) -> str:
        return "job-1"

    def bind_art_client(self, job_id: str, client: Any) -> None:
        self.bound = client

    async def mark_art_job_running(self, job_id: str) -> bool:
        return False

    async def finish_art_job(self, job_id: str) -> None:
        return None

    async def discard_art_job(self, job_id: str) -> None:
        return None


def _patch_start(
    monkeypatch: pytest.MonkeyPatch, calls: dict[str, Any]
) -> _FakeClient:
    """Patch start-route collaborators, recording provider-aware calls."""
    client = _FakeClient("muse", RuntimeMode.CLOUD)
    def fake_resolve(registry: Any, provider: str = "local") -> _FakeClient:
        calls["provider"] = provider
        return client
    async def fake_unload(req: Any, source: str = "") -> None:
        calls["unload"] = True

    allowed = SimpleNamespace(allowed=True, reason="")
    monkeypatch.setattr(start, "resolve_generation_model",
        lambda r: calls.__setitem__("model", True))
    monkeypatch.setattr(start, "resolve_art_client", fake_resolve)
    monkeypatch.setattr(start, "unload_llm_before_art", fake_unload)
    monkeypatch.setattr(start, "require_runtime_registry", lambda req: None)
    monkeypatch.setattr(start, "JobTracker", _FakeTracker)
    monkeypatch.setattr(start, "evaluate_prompt_fields", lambda f: allowed)
    return client


def test_muse_skips_local_model_and_unload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Muse skips local model resolution and the LLM unload."""
    calls: dict[str, Any] = {}
    _patch_start(monkeypatch, calls)
    assert asyncio.run(start.create_generation_job(
        GenerationRequest(prompt="a cat", provider="muse"),
        SimpleNamespace())) == "job-1"
    assert calls.get("provider") == "muse"
    assert "model" not in calls
    assert "unload" not in calls


def test_local_keeps_model_and_unload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Local keeps model resolution and the LLM unload."""
    calls: dict[str, Any] = {}
    _patch_start(monkeypatch, calls)
    assert asyncio.run(start.create_generation_job(
        GenerationRequest(prompt="a cat"), SimpleNamespace())) == "job-1"
    assert calls.get("provider") == "local"
    assert calls.get("model") is True
    assert calls.get("unload") is True
