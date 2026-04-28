"""Safe smoke tests for the daemon-backed art runtime path."""

import asyncio
import time
from types import SimpleNamespace

import pytest

from airunner.ipc.messages import EnvelopeStatus, ErrorEnvelope, ResponseEnvelope
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


pytestmark = [
    pytest.mark.art_runtime_smoke,
    pytest.mark.fast,
]


class FakeArtRuntimeClient:
    """Runtime client double for art smoke tests."""

    def __init__(self, *, delay: float = 0.0, script=None) -> None:
        self.delay = delay
        self.script = list(script or [])
        self.invocations = []
        self.cancelled = []
        self.descriptor = RuntimeDescriptor(
            runtime=RuntimeKind.ART,
            provider="local",
            mode=RuntimeMode.SIDECAR,
            transport=TransportKind.HTTP,
            endpoint="http://127.0.0.1:8190",
        )

    def invoke(self, request):
        self.invocations.append(request)
        if self.delay:
            time.sleep(self.delay)
        if self.script:
            next_response = self.script.pop(0)
            if callable(next_response):
                return next_response(request)
            return next_response
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


class FakeRuntimeRegistry:
    """Minimal runtime registry double for art smoke tests."""

    def __init__(self, client: FakeArtRuntimeClient) -> None:
        self.client = client

    def resolve(self, runtime, provider, deployment_mode="default"):
        assert runtime is RuntimeKind.ART
        assert provider == "local"
        assert deployment_mode == "sidecar"
        return self.client


def _request_for(client: FakeArtRuntimeClient) -> SimpleNamespace:
    return SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(runtime_registry=FakeRuntimeRegistry(client))
        )
    )


def _capture_tasks(monkeypatch):
    scheduled = []

    def fake_create_task(coroutine):
        scheduled.append(coroutine)
        return SimpleNamespace(done=lambda: False)

    monkeypatch.setattr(
        "airunner.api.routes.art.asyncio.create_task",
        fake_create_task,
    )
    return scheduled


async def _drain(coroutines):
    for coroutine in coroutines:
        await coroutine


def test_art_runtime_smoke_completes_job_via_runtime_boundary(monkeypatch):
    from airunner.api.routes.art import (
        GenerationRequest,
        generate_image,
        get_job_status,
    )

    client = FakeArtRuntimeClient()
    scheduled = _capture_tasks(monkeypatch)

    async def run_test():
        response = await generate_image(
            GenerationRequest(prompt="A bridge"),
            _request_for(client),
        )
        await _drain(scheduled)
        status = await get_job_status(response.job_id)
        return response, status

    response, status = asyncio.run(run_test())

    assert response.status == "running"
    assert status.status == "completed"
    assert client.invocations[0].runtime is RuntimeKind.ART


def test_art_runtime_smoke_recovers_after_failed_job(monkeypatch):
    from airunner.api.routes.art import (
        GenerationRequest,
        generate_image,
        get_job_status,
    )

    failing = ResponseEnvelope(
        request_id="art-fail-1",
        status=EnvelopeStatus.FAILED,
        error=ErrorEnvelope(
            code="art_invoke_failed",
            message="sidecar crashed",
            retryable=True,
        ),
    )
    client = FakeArtRuntimeClient(script=[failing])
    scheduled = _capture_tasks(monkeypatch)

    async def run_test():
        failed = await generate_image(
            GenerationRequest(prompt="Fail once"),
            _request_for(client),
        )
        recovered = await generate_image(
            GenerationRequest(prompt="Recover"),
            _request_for(client),
        )
        await _drain(scheduled)
        failed_status = await get_job_status(failed.job_id)
        recovered_status = await get_job_status(recovered.job_id)
        return failed_status, recovered_status

    failed_status, recovered_status = asyncio.run(run_test())

    assert failed_status.status == "failed"
    assert recovered_status.status == "completed"


def test_art_runtime_smoke_repeated_jobs_stay_isolated(monkeypatch):
    from airunner.api.routes.art import (
        GenerationRequest,
        generate_image,
        get_job_status,
    )

    client = FakeArtRuntimeClient()
    scheduled = _capture_tasks(monkeypatch)

    async def run_test():
        first = await generate_image(
            GenerationRequest(prompt="One"),
            _request_for(client),
        )
        second = await generate_image(
            GenerationRequest(prompt="Two"),
            _request_for(client),
        )
        await _drain(scheduled)
        first_status = await get_job_status(first.job_id)
        second_status = await get_job_status(second.job_id)
        return first, second, first_status, second_status

    first, second, first_status, second_status = asyncio.run(run_test())

    assert first.job_id != second.job_id
    assert first_status.status == "completed"
    assert second_status.status == "completed"
    assert [request.request_id for request in client.invocations] == [
        first.job_id,
        second.job_id,
    ]


@pytest.mark.benchmark
def test_art_runtime_smoke_metrics_are_logged(monkeypatch):
    """Capture lightweight repeated-job metrics for art runtime smoke runs."""
    from airunner.api.routes.art import (
        GenerationRequest,
        generate_image,
        get_job_status,
    )

    client = FakeArtRuntimeClient(delay=0.01)
    scheduled = _capture_tasks(monkeypatch)

    async def run_test():
        responses = [
            await generate_image(
                GenerationRequest(prompt=f"Prompt {index}"),
                _request_for(client),
            )
            for index in range(3)
        ]
        await _drain(scheduled)
        statuses = [await get_job_status(response.job_id) for response in responses]
        return responses, statuses

    started = time.perf_counter()
    responses, statuses = asyncio.run(run_test())
    elapsed = max(time.perf_counter() - started, 1e-9)
    average_latency_ms = (elapsed / len(responses)) * 1000
    throughput_rps = len(responses) / elapsed

    print(
        "Art runtime smoke metrics: "
        f"requests={len(responses)} "
        f"avg_latency_ms={average_latency_ms:.2f} "
        f"throughput_rps={throughput_rps:.2f}"
    )

    assert all(status.status == "completed" for status in statuses)
    assert average_latency_ms > 0
    assert throughput_rps > 0