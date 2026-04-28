"""Safe smoke tests for the daemon-backed TTS runtime path."""

import asyncio
import base64
import threading
import time
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from airunner.ipc.messages import EnvelopeStatus, ErrorEnvelope, ResponseEnvelope
from airunner.runtimes.contracts import (
    RuntimeDescriptor,
    RuntimeKind,
    RuntimeMode,
    TransportKind,
)


pytestmark = [
    pytest.mark.tts_runtime_smoke,
    pytest.mark.fast,
]


class FakeTTSRuntimeClient:
    """Runtime client double for TTS smoke tests."""

    def __init__(self, *, delay: float = 0.0, script=None) -> None:
        self.delay = delay
        self.script = list(script or [])
        self.invocations = []
        self._inflight = 0
        self.max_inflight = 0
        self._lock = threading.Lock()
        self.descriptor = RuntimeDescriptor(
            runtime=RuntimeKind.TTS,
            provider="local",
            mode=RuntimeMode.SIDECAR,
            transport=TransportKind.HTTP,
            endpoint="http://127.0.0.1:8191",
        )

    def invoke(self, request):
        self.invocations.append(request)
        with self._lock:
            self._inflight += 1
            self.max_inflight = max(self.max_inflight, self._inflight)
        try:
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
                payload={
                    "audio_b64": base64.b64encode(b"wav-bytes").decode("ascii")
                },
            )
        finally:
            with self._lock:
                self._inflight -= 1


class FakeRuntimeRegistry:
    """Minimal runtime registry double for TTS smoke tests."""

    def __init__(self, client: FakeTTSRuntimeClient) -> None:
        self.client = client

    def resolve(self, runtime, provider, deployment_mode="default"):
        assert runtime is RuntimeKind.TTS
        assert provider == "local"
        assert deployment_mode == "sidecar"
        return self.client


def _request_for(client: FakeTTSRuntimeClient) -> SimpleNamespace:
    return SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(runtime_registry=FakeRuntimeRegistry(client))
        )
    )


def test_tts_runtime_smoke_uses_runtime_boundary():
    from airunner.api.routes.tts import TTSRequest, synthesize_speech

    client = FakeTTSRuntimeClient()

    async def run_test():
        response = await synthesize_speech(
            TTSRequest(text="Hello there", request_id="tts-smoke-1"),
            _request_for(client),
        )
        chunk = await response.body_iterator.__anext__()
        return response, chunk

    response, chunk = asyncio.run(run_test())

    assert response.media_type == "audio/wav"
    assert chunk == b"wav-bytes"
    assert client.invocations[0].request_id == "tts-smoke-1"


def test_tts_runtime_smoke_recovers_after_failure():
    from airunner.api.routes.tts import TTSRequest, synthesize_speech

    failing = ResponseEnvelope(
        request_id="tts-fail-1",
        status=EnvelopeStatus.FAILED,
        error=ErrorEnvelope(
            code="tts_invoke_failed",
            message="sidecar crashed",
            retryable=True,
        ),
    )
    client = FakeTTSRuntimeClient(script=[failing])

    async def run_test():
        with pytest.raises(HTTPException):
            await synthesize_speech(
                TTSRequest(text="Fail once", request_id="tts-fail-1"),
                _request_for(client),
            )
        response = await synthesize_speech(
            TTSRequest(text="Recover", request_id="tts-ok-1"),
            _request_for(client),
        )
        chunk = await response.body_iterator.__anext__()
        return chunk

    chunk = asyncio.run(run_test())

    assert chunk == b"wav-bytes"


def test_tts_runtime_smoke_repeated_requests_keep_request_ids_isolated():
    from airunner.api.routes.tts import TTSRequest, synthesize_speech

    client = FakeTTSRuntimeClient(delay=0.01)

    async def invoke_many():
        first = synthesize_speech(
            TTSRequest(text="One", request_id="tts-one"),
            _request_for(client),
        )
        second = synthesize_speech(
            TTSRequest(text="Two", request_id="tts-two"),
            _request_for(client),
        )
        return await asyncio.gather(first, second)

    responses = asyncio.run(invoke_many())

    assert len(responses) == 2
    assert {request.request_id for request in client.invocations} == {
        "tts-one",
        "tts-two",
    }
    assert client.max_inflight >= 2


@pytest.mark.benchmark
def test_tts_runtime_smoke_metrics_are_logged():
    """Capture lightweight repeated-request metrics for TTS smoke runs."""
    from airunner.api.routes.tts import TTSRequest, synthesize_speech

    client = FakeTTSRuntimeClient(delay=0.01)

    async def invoke_many():
        responses = await asyncio.gather(
            synthesize_speech(
                TTSRequest(text="Metric one", request_id="tts-metric-1"),
                _request_for(client),
            ),
            synthesize_speech(
                TTSRequest(text="Metric two", request_id="tts-metric-2"),
                _request_for(client),
            ),
            synthesize_speech(
                TTSRequest(text="Metric three", request_id="tts-metric-3"),
                _request_for(client),
            ),
        )
        chunks = [await response.body_iterator.__anext__() for response in responses]
        return chunks

    started = time.perf_counter()
    chunks = asyncio.run(invoke_many())
    elapsed = max(time.perf_counter() - started, 1e-9)
    average_latency_ms = (elapsed / len(chunks)) * 1000
    throughput_rps = len(chunks) / elapsed

    print(
        "TTS runtime smoke metrics: "
        f"requests={len(chunks)} "
        f"avg_latency_ms={average_latency_ms:.2f} "
        f"throughput_rps={throughput_rps:.2f}"
    )

    assert all(chunk == b"wav-bytes" for chunk in chunks)
    assert average_latency_ms > 0
    assert throughput_rps > 0