"""Tests for the art runtime-backed route."""

import asyncio
import base64
from types import SimpleNamespace

from airunner.ipc.messages import EnvelopeStatus, ResponseEnvelope
from airunner.runtimes.contracts import (
    RuntimeDescriptor,
    RuntimeKind,
    RuntimeMode,
    TransportKind,
)

PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
    "/w8AAn8B9pN96QAAAABJRU5ErkJggg=="
)


class FakeArtRuntimeClient:
    """Runtime client double for direct art route tests."""

    def __init__(self):
        self.descriptor = RuntimeDescriptor(
            runtime=RuntimeKind.ART,
            provider="local",
            mode=RuntimeMode.SIDECAR,
            transport=TransportKind.HTTP,
            endpoint="http://127.0.0.1:8190",
        )
        self.invocations = []
        self.cancelled = []

    def invoke(self, request):
        self.invocations.append(request)
        return ResponseEnvelope(
            request_id=request.request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload={"images": [PNG_B64], "image_count": 1},
        )

    def cancel(self, request_id: str):
        self.cancelled.append(request_id)
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.CANCELLED,
        )


class FakeRegistry:
    """Runtime registry double for direct art route tests."""

    def __init__(self, client):
        self.client = client

    def resolve(self, runtime, provider, deployment_mode="default"):
        assert runtime is RuntimeKind.ART
        assert provider == "local"
        assert deployment_mode == "sidecar"
        return self.client


def _request_for(client):
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(runtime_registry=FakeRegistry(client))))


def test_generate_image_runs_art_runtime_job(monkeypatch):
    from airunner.api.routes.art import GenerationRequest, generate_image, get_job_status, get_result

    client = FakeArtRuntimeClient()
    scheduled = []

    def fake_create_task(coroutine):
        scheduled.append(coroutine)
        return SimpleNamespace(done=lambda: False)

    async def run_test():
        monkeypatch.setattr("airunner.api.routes.art.asyncio.create_task", fake_create_task)
        response = await generate_image(GenerationRequest(prompt="A lighthouse"), _request_for(client))
        await scheduled[0]
        status = await get_job_status(response.job_id)
        result = await get_result(response.job_id)
        chunk = await result.body_iterator.__anext__()
        return response, status, chunk

    response, status, chunk = asyncio.run(run_test())

    assert response.status == "running"
    assert status.status == "completed"
    assert chunk.startswith(b"\x89PNG")
    assert client.invocations[0].request_id == response.job_id


def test_cancel_job_routes_cancellation_through_runtime(monkeypatch):
    from airunner.api.routes.art import GenerationRequest, cancel_job, generate_image, get_job_status

    client = FakeArtRuntimeClient()
    scheduled = []

    def fake_create_task(coroutine):
        scheduled.append(coroutine)
        return SimpleNamespace(done=lambda: False)

    async def run_test():
        monkeypatch.setattr("airunner.api.routes.art.asyncio.create_task", fake_create_task)
        response = await generate_image(GenerationRequest(prompt="A tree"), _request_for(client))
        cancelled = await cancel_job(response.job_id, _request_for(client))
        await scheduled[0]
        status = await get_job_status(response.job_id)
        return response, cancelled, status

    response, cancelled, status = asyncio.run(run_test())

    assert cancelled["status"] == "cancelled"
    assert client.cancelled == [response.job_id]
    assert status.status == "cancelled"