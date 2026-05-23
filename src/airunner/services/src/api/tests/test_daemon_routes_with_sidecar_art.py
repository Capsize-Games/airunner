"""Tests for daemon routes with the explicit art sidecar runtime."""

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


class FakeSidecarArtClient:
    """Runtime client double for daemon route tests."""

    def __init__(self) -> None:
        self.descriptor = RuntimeDescriptor(
            runtime=RuntimeKind.ART,
            provider="local",
            mode=RuntimeMode.SIDECAR,
            transport=TransportKind.HTTP,
            endpoint="http://127.0.0.1:8190",
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
    """Registry double that only exposes the art sidecar route."""

    def __init__(self, client) -> None:
        self.route_map = {
            RuntimeRoute(
                RuntimeKind.ART,
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


def test_get_runtime_status_resolves_explicit_sidecar_art_route():
    from airunner_api.routes.daemon import get_runtime_status

    client = FakeSidecarArtClient()
    response = asyncio.run(
        get_runtime_status(
            "art",
            _request_for(FakeRegistry(client)),
            provider="local",
            deployment_mode="sidecar",
        )
    )

    assert response.runtime == "art"
    assert response.transport == "http"


def test_load_runtime_uses_explicit_sidecar_art_route():
    from airunner_api.routes.daemon import RuntimeRouteRequest, load_runtime

    client = FakeSidecarArtClient()
    response = asyncio.run(
        load_runtime(
            "art",
            RuntimeRouteRequest(
                request_id="art-load-1",
                deployment_mode="sidecar",
            ),
            _request_for(FakeRegistry(client)),
        )
    )

    assert client.invocations[0].action.value == "load_model"
    assert response.status is EnvelopeStatus.SUCCEEDED


def test_cancel_runtime_uses_explicit_sidecar_art_route():
    from airunner_api.routes.daemon import RuntimeRouteRequest, cancel_runtime

    client = FakeSidecarArtClient()
    response = asyncio.run(
        cancel_runtime(
            "art",
            RuntimeRouteRequest(
                request_id="art-cancel-1",
                deployment_mode="sidecar",
            ),
            _request_for(FakeRegistry(client)),
        )
    )

    assert client.cancelled_ids == ["art-cancel-1"]
    assert response.status is EnvelopeStatus.CANCELLED