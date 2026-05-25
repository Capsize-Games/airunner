"""Tests for the art runtime-backed route."""

import asyncio
import base64
from types import SimpleNamespace

import pytest

from airunner_services.ipc.messages import EnvelopeStatus, ResponseEnvelope
from airunner_services.contract_enums import ModelStatus
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
        if request.action.name == "LOAD_MODEL":
            return ResponseEnvelope(
                request_id=request.request_id,
                status=EnvelopeStatus.SUCCEEDED,
                payload={
                    "accepted": True,
                    "component": request.metadata.get("component"),
                },
            )
        if request.action.name == "UNLOAD_MODEL":
            return ResponseEnvelope(
                request_id=request.request_id,
                status=EnvelopeStatus.SUCCEEDED,
                payload={
                    "accepted": True,
                    "component": request.metadata.get("component"),
                },
            )
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


class FakeLifecycleService:
    """Lifecycle double that exposes daemon LLM unload state."""

    def __init__(self, statuses):
        self._statuses = list(statuses)
        self.unload_sources = []

    def current_llm_model_status(self):
        if len(self._statuses) > 1:
            return self._statuses.pop(0)
        if self._statuses:
            return self._statuses[0]
        return None

    def queue_llm_unload(self, source="daemon_admin_unload"):
        self.unload_sources.append(source)
        return True


def _request_for(client, lifecycle_service=None):
    state = SimpleNamespace(runtime_registry=FakeRegistry(client))
    if lifecycle_service is not None:
        state.lifecycle_service = lifecycle_service
    return SimpleNamespace(app=SimpleNamespace(state=state))


def test_generate_image_runs_art_runtime_job(monkeypatch):
    from airunner_api.routes.art import GenerationRequest, generate_image, get_job_status, get_result

    client = FakeArtRuntimeClient()
    scheduled = []

    def fake_create_task(coroutine):
        scheduled.append(coroutine)
        return SimpleNamespace(done=lambda: False)

    async def run_test():
        monkeypatch.setattr("airunner_api.routes.art.asyncio.create_task", fake_create_task)
        response = await generate_image(GenerationRequest(prompt="A lighthouse"), _request_for(client))
        await scheduled[0]
        status = await get_job_status(response.job_id)
        result = await get_result(response.job_id)
        return response, status, result.body

    response, status, chunk = asyncio.run(run_test())

    assert response.status == "running"
    assert status.status == "completed"
    assert chunk.startswith(b"\x89PNG")
    assert client.invocations[0].request_id == response.job_id


def test_generate_image_unloads_daemon_llm_before_art(monkeypatch):
    from airunner_api.routes.art import GenerationRequest, generate_image

    client = FakeArtRuntimeClient()
    lifecycle = FakeLifecycleService(
        [ModelStatus.LOADED, ModelStatus.UNLOADED]
    )
    scheduled = []

    async def fake_sleep(_seconds):
        return None

    def fake_create_task(coroutine):
        scheduled.append(coroutine)
        return SimpleNamespace(done=lambda: False)

    async def run_test():
        monkeypatch.setattr(
            "airunner_api.routes.art.asyncio.create_task",
            fake_create_task,
        )
        monkeypatch.setattr(
            "airunner_api.routes.art.asyncio.sleep",
            fake_sleep,
        )
        response = await generate_image(
            GenerationRequest(prompt="A lighthouse"),
            _request_for(client, lifecycle),
        )
        assert lifecycle.unload_sources == ["art_generate"]
        assert client.invocations == []
        await scheduled[0]
        return response

    response = asyncio.run(run_test())

    assert response.status == "running"
    assert client.invocations[0].request_id == response.job_id


def test_cancel_job_routes_cancellation_through_runtime(monkeypatch):
    from airunner_api.routes.art import GenerationRequest, cancel_job, generate_image, get_job_status

    client = FakeArtRuntimeClient()
    scheduled = []

    def fake_create_task(coroutine):
        scheduled.append(coroutine)
        return SimpleNamespace(done=lambda: False)

    async def run_test():
        monkeypatch.setattr("airunner_api.routes.art.asyncio.create_task", fake_create_task)
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
    from airunner_api.routes.art import GenerationRequest, generate_image
    from airunner_services.utils.job_tracker import JobTracker

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
            "airunner_api.routes.art.asyncio.create_task",
            fake_create_task,
        )
        monkeypatch.setattr(
            "airunner_api.routes.art.JobTracker.update_progress",
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


def test_generate_image_can_mark_job_to_skip_auto_export(monkeypatch):
    from airunner_api.routes.art import GenerationRequest, generate_image

    client = FakeArtRuntimeClient()
    scheduled = []

    def fake_create_task(coroutine):
        scheduled.append(coroutine)
        return SimpleNamespace(done=lambda: False)

    async def run_test():
        monkeypatch.setattr(
            "airunner_api.routes.art.asyncio.create_task",
            fake_create_task,
        )
        response = await generate_image(
            GenerationRequest(
                prompt="A lighthouse",
                skip_auto_export=True,
            ),
            _request_for(client),
        )
        await scheduled[0]
        return response

    response = asyncio.run(run_test())

    assert response.status == "running"
    assert client.invocations[0].payload["metadata"]["skip_auto_export"] is True


def test_generate_image_can_forward_img2img_metadata(monkeypatch):
    from airunner_api.routes.art import GenerationRequest, generate_image

    client = FakeArtRuntimeClient()
    scheduled = []

    def fake_create_task(coroutine):
        scheduled.append(coroutine)
        return SimpleNamespace(done=lambda: False)

    async def run_test():
        monkeypatch.setattr(
            "airunner_api.routes.art.asyncio.create_task",
            fake_create_task,
        )
        response = await generate_image(
            GenerationRequest(
                prompt="A lighthouse",
                pipeline="img2img",
                strength=0.35,
                image_b64="cG5nLWJ5dGVz",
            ),
            _request_for(client),
        )
        await scheduled[0]
        return response

    response = asyncio.run(run_test())

    assert response.status == "running"
    metadata = client.invocations[0].payload["metadata"]
    assert metadata["pipeline"] == "img2img"
    assert metadata["strength"] == 0.35
    assert metadata["image_b64"] == "cG5nLWJ5dGVz"


def test_get_result_prefers_cached_png_bytes():
    from airunner_api.routes.art import get_result
    from airunner_services.utils.job_tracker import JobTracker

    async def run_test():
        tracker = JobTracker()
        job_id = await tracker.create_job()
        await tracker.complete_job(
            job_id,
            {"image_bytes": base64.b64decode(PNG_B64)},
        )
        result = await get_result(job_id)
        return result.body

    chunk = asyncio.run(run_test())

    assert chunk == base64.b64decode(PNG_B64)


def test_resolve_art_client_requires_explicit_sidecar_route():
    from airunner_api.routes.art import resolve_art_client
    from airunner.runtimes.registry import RuntimeRegistry

    with pytest.raises(Exception) as exc_info:
        resolve_art_client(RuntimeRegistry())

    assert getattr(exc_info.value, "status_code", None) == 503
    assert "Art sidecar runtime unavailable" in str(exc_info.value.detail)


def test_resolve_art_client_uses_local_fallback_inside_sidecar(monkeypatch):
    from airunner_api.routes.art import resolve_art_client

    client = FakeArtRuntimeClient()
    monkeypatch.setenv("AIRUNNER_ART_SIDECAR_PROCESS", "1")

    resolved = resolve_art_client(FakeSidecarProcessRegistry(client))

    assert resolved is client


def test_remove_background_routes_through_art_runtime():
    from airunner_api.routes.art import BackgroundRemovalRequest, remove_background

    client = FakeArtRuntimeClient()

    async def run_test():
        response = await remove_background(
            BackgroundRemovalRequest(image_b64="cG5n"),
            _request_for(client),
        )
        return response.body

    chunk = asyncio.run(run_test())

    assert chunk.startswith(b"\x89PNG")
    assert client.invocations[-1].metadata["operation"] == "remove_background"


def test_art_component_routes_forward_component_control():
    from airunner_api.routes.art import load_art_component, unload_art_component

    client = FakeArtRuntimeClient()

    async def run_test():
        loaded = await load_art_component("rmbg", _request_for(client))
        unloaded = await unload_art_component(
            "safety_checker",
            _request_for(client),
        )
        return loaded, unloaded

    loaded, unloaded = asyncio.run(run_test())

    assert loaded.status == "loaded"
    assert unloaded.status == "unloaded"
    assert client.invocations[0].metadata["component"] == "rmbg"
    assert client.invocations[1].metadata["component"] == "safety_checker"