"""Tests for daemon runtime status and control routes."""

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from airunner.ipc.messages import ErrorEnvelope, EnvelopeStatus, ResponseEnvelope
from airunner.runtimes.contracts import (
    RuntimeDescriptor,
    RuntimeHealth,
    RuntimeHealthStatus,
    RuntimeKind,
    RuntimeMode,
    TransportKind,
)
from airunner.runtimes.registry import RuntimeRoute


class FakeRuntimeClient:
    """Runtime client double for daemon route tests."""

    def __init__(
        self,
        runtime: RuntimeKind,
        *,
        status: RuntimeHealthStatus = RuntimeHealthStatus.UNKNOWN,
        allows_model_control: bool = True,
    ) -> None:
        self.descriptor = RuntimeDescriptor(
            runtime=runtime,
            provider="local",
            mode=RuntimeMode.LOCAL_FALLBACK,
            transport=TransportKind.IN_PROCESS,
            allows_model_control=allows_model_control,
        )
        self._status = status
        self.invocations = []
        self.cancelled_ids = []
        self.invoke_response = None

    def healthcheck(self) -> RuntimeHealth:
        """Return the configured runtime health payload."""
        return RuntimeHealth(
            descriptor=self.descriptor,
            status=self._status,
        )

    def invoke(self, request):
        """Record and return a control response."""
        self.invocations.append(request)
        if self.invoke_response is not None:
            return self.invoke_response
        return ResponseEnvelope(
            request_id=request.request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload={"action": request.action.value},
        )

    def cancel(self, request_id: str) -> ResponseEnvelope:
        """Record and return a cancellation response."""
        self.cancelled_ids.append(request_id)
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.CANCELLED,
            metadata={"best_effort": True},
        )


class FakeRegistry:
    """Registry double for direct daemon route testing."""

    def __init__(self, route_map):
        self.route_map = route_map

    def list_routes(self):
        """Return the registered runtime routes."""
        return tuple(self.route_map.keys())

    def resolve(self, runtime, provider, deployment_mode):
        """Resolve a runtime route from the in-memory route map."""
        route = RuntimeRoute(runtime, provider, deployment_mode).normalized()
        if route not in self.route_map:
            raise KeyError(route)
        return self.route_map[route]


def _fake_request(registry, loaded_models=None):
    """Build a minimal FastAPI request double for direct route calls."""
    status = {
        "lifecycle_initialized": True,
        "worker_manager_ready": True,
        "model_load_balancer_ready": True,
        "loaded_models": loaded_models or [],
        "runtime_registry_ready": registry is not None,
        "embedded_api_server_running": False,
        "preloaded_model_path": None,
    }
    return SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                runtime_registry=registry,
                lifecycle_service=SimpleNamespace(get_status=lambda: status),
            )
        )
    )


def test_list_runtimes_deduplicates_aliases_and_infers_loaded_state():
    """Daemon runtime listing should collapse aliases into one summary."""
    from airunner.api.routes.daemon import list_runtimes

    client = FakeRuntimeClient(RuntimeKind.LLM)
    registry = FakeRegistry(
        {
            RuntimeRoute(RuntimeKind.LLM, provider="local").normalized(): client,
            RuntimeRoute(
                RuntimeKind.LLM,
                provider="local",
                deployment_mode="local_fallback",
            ).normalized(): client,
        }
    )

    response = asyncio.run(list_runtimes(_fake_request(registry, ["LLM"])))

    assert len(response) == 1
    assert response[0].runtime == "llm"
    assert response[0].status == "ready"
    assert response[0].loaded is True
    assert response[0].route_aliases == [
        "local:default",
        "local:local_fallback",
    ]


def test_daemon_runtime_status_includes_lifecycle_and_runtimes():
    """Combined daemon status should include lifecycle and runtime data."""
    from airunner.api.routes.daemon import daemon_runtime_status

    client = FakeRuntimeClient(RuntimeKind.STT, status=RuntimeHealthStatus.READY)
    registry = FakeRegistry(
        {
            RuntimeRoute(
                RuntimeKind.STT,
                provider="local",
                deployment_mode="local_fallback",
            ).normalized(): client,
        }
    )

    response = asyncio.run(daemon_runtime_status(_fake_request(registry)))

    assert response.lifecycle.lifecycle_initialized is True
    assert response.runtimes[0].runtime == "stt"
    assert response.runtimes[0].status == "ready"


def test_get_runtime_status_returns_requested_runtime():
    """Runtime detail should resolve the requested daemon route."""
    from airunner.api.routes.daemon import get_runtime_status

    client = FakeRuntimeClient(RuntimeKind.TTS, status=RuntimeHealthStatus.READY)
    registry = FakeRegistry(
        {
            RuntimeRoute(
                RuntimeKind.TTS,
                provider="local",
                deployment_mode="local_fallback",
            ).normalized(): client,
        }
    )

    response = asyncio.run(
        get_runtime_status(
            "tts",
            _fake_request(registry),
            provider="local",
            deployment_mode="local_fallback",
        )
    )

    assert response.runtime == "tts"
    assert response.transport == "in_process"


def test_load_runtime_invokes_control_action():
    """Load requests should emit a runtime load envelope."""
    from airunner.api.routes.daemon import RuntimeRouteRequest, load_runtime

    client = FakeRuntimeClient(RuntimeKind.LLM)
    registry = FakeRegistry(
        {
            RuntimeRoute(RuntimeKind.LLM, provider="local").normalized(): client,
        }
    )

    response = asyncio.run(
        load_runtime(
            "llm",
            RuntimeRouteRequest(request_id="load-1"),
            _fake_request(registry),
        )
    )

    assert client.invocations[0].action.value == "load_model"
    assert response.status is EnvelopeStatus.SUCCEEDED


def test_unload_runtime_invokes_control_action():
    """Unload requests should emit a runtime unload envelope."""
    from airunner.api.routes.daemon import RuntimeRouteRequest, unload_runtime

    client = FakeRuntimeClient(RuntimeKind.LLM)
    registry = FakeRegistry(
        {
            RuntimeRoute(RuntimeKind.LLM, provider="local").normalized(): client,
        }
    )

    response = asyncio.run(
        unload_runtime(
            "llm",
            RuntimeRouteRequest(request_id="unload-1"),
            _fake_request(registry),
        )
    )

    assert client.invocations[0].action.value == "unload_model"
    assert response.status is EnvelopeStatus.SUCCEEDED


def test_cancel_runtime_uses_client_cancellation():
    """Cancel requests should be delegated to the runtime client."""
    from airunner.api.routes.daemon import RuntimeRouteRequest, cancel_runtime

    client = FakeRuntimeClient(RuntimeKind.STT)
    registry = FakeRegistry(
        {
            RuntimeRoute(RuntimeKind.STT, provider="local").normalized(): client,
        }
    )

    response = asyncio.run(
        cancel_runtime(
            "stt",
            RuntimeRouteRequest(request_id="cancel-1"),
            _fake_request(registry),
        )
    )

    assert client.cancelled_ids == ["cancel-1"]
    assert response.status is EnvelopeStatus.CANCELLED


def test_load_runtime_surfaces_runtime_failures():
    """Runtime control failures should map to HTTP errors."""
    from airunner.api.routes.daemon import RuntimeRouteRequest, load_runtime

    client = FakeRuntimeClient(RuntimeKind.ART, allows_model_control=False)
    client.invoke_response = ResponseEnvelope(
        request_id="art-load-1",
        status=EnvelopeStatus.FAILED,
        error=ErrorEnvelope(
            code="art_load_unsupported",
            message="Art loading is request-driven",
        ),
    )
    registry = FakeRegistry(
        {
            RuntimeRoute(RuntimeKind.ART, provider="local").normalized(): client,
        }
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            load_runtime(
                "art",
                RuntimeRouteRequest(request_id="art-load-1"),
                _fake_request(registry),
            )
        )

    assert exc_info.value.status_code == 409