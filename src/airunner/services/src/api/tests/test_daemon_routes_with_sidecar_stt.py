"""Tests for daemon routes with the explicit STT sidecar runtime route."""

import asyncio
from types import SimpleNamespace

from airunner_services.ipc.messages import EnvelopeStatus, ResponseEnvelope
from airunner.runtimes.contracts import (
    RuntimeDescriptor,
    RuntimeKind,
    RuntimeMode,
    TransportKind,
)
from airunner.runtimes.registry import RuntimeRoute


class FakeSidecarSTTClient:
    """Runtime client double for daemon route tests."""

    def __init__(self) -> None:
        self.descriptor = RuntimeDescriptor(
            runtime=RuntimeKind.STT,
            provider="local",
            mode=RuntimeMode.SIDECAR,
            transport=TransportKind.HTTP,
            endpoint="http://127.0.0.1:8012",
        )
        self.invocations = []
        self.cancelled_ids = []

    def healthcheck(self):
        from airunner.runtimes.contracts import RuntimeHealth, RuntimeHealthStatus

        return RuntimeHealth(
            descriptor=self.descriptor,
            status=RuntimeHealthStatus.READY,
        )

    def invoke(self, request):
        self.invocations.append(request)
        return ResponseEnvelope(
            request_id=request.request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload={"action": request.action.value},
        )

    def cancel(self, request_id: str):
        self.cancelled_ids.append(request_id)
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.CANCELLED,
        )


class FakeRegistry:
    """Registry double that only exposes the STT sidecar route."""

    def __init__(self, client) -> None:
        self.route_map = {
            RuntimeRoute(
                RuntimeKind.STT,
                provider="local",
                deployment_mode="sidecar",
            ).normalized(): client,
        }

    def list_routes(self):
        return tuple(self.route_map.keys())

    def resolve(self, runtime, provider, deployment_mode):
        route = RuntimeRoute(runtime, provider, deployment_mode).normalized()
        return self.route_map[route]


def _request_for(registry):
    status = {
        "lifecycle_initialized": True,
        "worker_manager_ready": True,
        "model_load_balancer_ready": True,
        "loaded_models": [],
        "runtime_registry_ready": True,
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


def test_get_runtime_status_resolves_explicit_sidecar_stt_route():
    from airunner_api.routes.daemon import get_runtime_status

    client = FakeSidecarSTTClient()
    response = asyncio.run(
        get_runtime_status(
            "stt",
            _request_for(FakeRegistry(client)),
            provider="local",
            deployment_mode="sidecar",
        )
    )

    assert response.runtime == "stt"
    assert response.transport == "http"


def test_cancel_runtime_uses_explicit_sidecar_stt_route():
    from airunner_api.routes.daemon import RuntimeRouteRequest, cancel_runtime

    client = FakeSidecarSTTClient()
    response = asyncio.run(
        cancel_runtime(
            "stt",
            RuntimeRouteRequest(
                request_id="sidecar-cancel-1",
                deployment_mode="sidecar",
            ),
            _request_for(FakeRegistry(client)),
        )
    )

    assert client.cancelled_ids == ["sidecar-cancel-1"]
    assert response.status is EnvelopeStatus.CANCELLED