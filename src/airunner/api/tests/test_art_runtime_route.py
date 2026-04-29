"""Tests for the art runtime-backed route."""

import asyncio
import base64
from types import SimpleNamespace

import pytest

from airunner.ipc.messages import EnvelopeStatus, ResponseEnvelope
from airunner.runtimes.contracts import (
    RuntimeDescriptor,
    RuntimeKind,
    RuntimeMode,
    TransportKind,
)

PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4"
    "//8/AwAI/AL+KDvWyAAAAABJRU5ErkJggg=="
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


class FakeProgressArtRuntimeClient(FakeArtRuntimeClient):
    """Runtime client double that reports progress before completion."""

    def invoke_with_progress(self, request, progress_callback):
        progress_callback({"status": "running", "progress": 40.0})
        return self.invoke(request)


class FakeRegistry:
    """Runtime registry double for direct art route tests."""

    def __init__(self, client):
        self.client = client
        self.routes = {
            (RuntimeKind.ART, "local", "sidecar"),
        }

    def has_route(self, route):
        normalized = route.normalized()
        return (
            normalized.runtime,
            normalized.provider,
            normalized.deployment_mode,
        ) in self.routes

    def resolve(self, runtime, provider, deployment_mode="default"):
        assert runtime is RuntimeKind.ART
        assert provider == "local"
        assert deployment_mode == "sidecar"
        return self.client


class FakeSidecarProcessRegistry(FakeRegistry):
    """Registry double for the dedicated art sidecar process."""

    def __init__(self, client):
        super().__init__(client)
        self.routes = {
            (RuntimeKind.ART, "local", "local_fallback"),
        }

    def resolve(self, runtime, provider, deployment_mode="default"):
        assert runtime is RuntimeKind.ART
        assert provider == "local"
        assert deployment_mode == "local_fallback"
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


def test_generate_image_updates_job_progress_when_runtime_reports_it(
    monkeypatch,
):
    from airunner.api.routes.art import GenerationRequest, generate_image
    from airunner.utils.job_tracker import JobTracker

    client = FakeProgressArtRuntimeClient()
    scheduled = []
    recorded_progress = []
    original_update_progress = JobTracker.update_progress

    def fake_create_task(coroutine):
        scheduled.append(coroutine)
        return SimpleNamespace(done=lambda: False)

    async def fake_update_progress(self, job_id, progress, status=None):
        recorded_progress.append((job_id, progress, status))
        await original_update_progress(self, job_id, progress, status)

    async def run_test():
        monkeypatch.setattr(
            "airunner.api.routes.art.asyncio.create_task",
            fake_create_task,
        )
        monkeypatch.setattr(
            "airunner.utils.job_tracker.JobTracker.update_progress",
            fake_update_progress,
        )
        response = await generate_image(
            GenerationRequest(prompt="A lighthouse"),
            _request_for(client),
        )
        await scheduled[0]
        return response

    response = asyncio.run(run_test())

    assert response.status == "running"
    assert any(job_id == response.job_id and progress == 40.0 for job_id, progress, _status in recorded_progress)


def test_resolve_art_client_requires_explicit_sidecar_route():
    from airunner.api.routes.art import resolve_art_client
    from airunner.runtimes.registry import RuntimeRegistry

    with pytest.raises(Exception) as exc_info:
        resolve_art_client(RuntimeRegistry())

    assert getattr(exc_info.value, "status_code", None) == 503
    assert "Art sidecar runtime unavailable" in str(exc_info.value.detail)


def test_resolve_art_client_uses_local_fallback_inside_sidecar(monkeypatch):
    from airunner.api.routes.art import resolve_art_client

    client = FakeArtRuntimeClient()
    monkeypatch.setenv("AIRUNNER_ART_SIDECAR_PROCESS", "1")

    resolved = resolve_art_client(FakeSidecarProcessRegistry(client))

    assert resolved is client