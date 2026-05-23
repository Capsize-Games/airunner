"""Safe smoke tests for the daemon-backed STT runtime path."""

import asyncio
import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from airunner_services.ipc.messages import (
    EnvelopeStatus,
    ErrorEnvelope,
    ResponseEnvelope,
)
from airunner.runtimes.contracts import (
    RuntimeAction,
    RuntimeDescriptor,
    RuntimeKind,
    RuntimeMode,
    TransportKind,
)


pytestmark = [
    pytest.mark.stt_runtime_smoke,
    pytest.mark.fast,
]


class FakeSTTRuntimeClient:
    """Runtime client double for STT smoke tests."""

    def __init__(self, *, delay: float = 0.0, script=None) -> None:
        self.delay = delay
        self.script = list(script or [])
        self.loaded = True
        self.invocations = []
        self.descriptor = RuntimeDescriptor(
            runtime=RuntimeKind.STT,
            provider="local",
            mode=RuntimeMode.SIDECAR,
            transport=TransportKind.HTTP,
        )

    def invoke(self, request):
        """Record runtime requests and return one scripted response."""
        self.invocations.append(request)
        if self.delay:
            time.sleep(self.delay)
        if self.script:
            next_response = self.script.pop(0)
            if callable(next_response):
                return next_response(request)
            return next_response
        if request.action is RuntimeAction.LOAD_MODEL:
            self.loaded = True
            return self._response(request.request_id, action="load_model")
        if request.action is RuntimeAction.UNLOAD_MODEL:
            self.loaded = False
            return self._response(request.request_id, action="unload_model")
        if not self.loaded:
            return ResponseEnvelope(
                request_id=request.request_id,
                status=EnvelopeStatus.FAILED,
                error=ErrorEnvelope(
                    code="stt_unloaded",
                    message="STT runtime is not loaded",
                ),
            )
        return self._response(
            request.request_id,
            text="runtime transcript",
            language=request.payload.get("language") or "en",
        )

    @staticmethod
    def _response(request_id: str, **payload) -> ResponseEnvelope:
        """Build one success envelope."""
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload=payload,
        )


class FakeRuntimeRegistry:
    """Minimal runtime registry double for smoke tests."""

    def __init__(self, client: FakeSTTRuntimeClient) -> None:
        self.client = client

    def resolve(self, runtime, provider, deployment_mode="default"):
        """Resolve the only supported local STT runtime."""
        return self.client


class FakeUploadFile:
    """UploadFile double for direct route tests."""

    def __init__(self, filename: str, content_type: str, data: bytes):
        self.filename = filename
        self.content_type = content_type
        self._data = data

    async def read(self):
        """Return the configured file bytes."""
        return self._data


class FakeDaemonSTTClient:
    """Daemon client double for live-audio smoke tests."""

    def __init__(self, responses, *, delay: float = 0.0) -> None:
        self.responses = list(responses)
        self.delay = delay
        self.calls = []

    def transcribe_audio(self, audio_bytes, *, mime_type, auto_start=True):
        """Return one configured live-audio response."""
        self.calls.append((audio_bytes, mime_type, auto_start))
        if self.delay:
            time.sleep(self.delay)
        next_response = self.responses.pop(0)
        if isinstance(next_response, Exception):
            raise next_response
        return next_response


def _request_for(registry) -> SimpleNamespace:
    """Build a minimal HTTP request double."""
    return SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(runtime_registry=registry))
    )


def _worker_for(client: FakeDaemonSTTClient):
    """Build an audio processor worker bound to one daemon client."""
    from airunner.components.stt.workers.audio_processor_worker import (
        AudioProcessorWorker,
    )

    worker = AudioProcessorWorker.__new__(AudioProcessorWorker)
    worker._executor = SimpleNamespace(
        stt_is_loaded=False,
        transcribe=MagicMock(),
    )
    worker.logger = MagicMock()
    worker.api = SimpleNamespace(
        daemon_client=client,
        headless=False,
        stt=SimpleNamespace(audio_processor_response=MagicMock()),
    )
    return worker


def _audio_file() -> FakeUploadFile:
    """Return one repeatable audio upload double."""
    return FakeUploadFile("clip.wav", "audio/wav", b"fake-audio")


def test_stt_file_upload_smoke_uses_runtime_boundary():
    """File transcription should flow through the STT runtime client."""
    from airunner_api.routes.stt import transcribe_audio

    client = FakeSTTRuntimeClient()
    response = asyncio.run(
        transcribe_audio(
            audio=_audio_file(),
            req=_request_for(FakeRuntimeRegistry(client)),
        )
    )

    assert response.text == "runtime transcript"
    assert response.language == "en"
    assert client.invocations[0].action is RuntimeAction.INVOKE


def test_stt_live_audio_smoke_uses_daemon_bridge():
    """Live audio should be transcribed through the GUI daemon client."""
    from airunner.components.stt.workers.audio_processor_worker import (
        AudioProcessorWorker,
    )

    daemon_client = FakeDaemonSTTClient([{"text": "heard phrase"}])
    worker = _worker_for(daemon_client)

    AudioProcessorWorker.handle_message(worker, {"item": b"\x01\x00"})

    assert daemon_client.calls == [
        (b"\x01\x00", "application/octet-stream", True)
    ]
    worker.api.stt.audio_processor_response.assert_called_once_with(
        "heard phrase"
    )


def test_stt_timeout_smoke_maps_to_gateway_timeout():
    """Timeout failures should be surfaced as HTTP 504 responses."""
    from airunner_api.routes.stt import transcribe_audio

    timeout_response = ResponseEnvelope(
        request_id="timeout-1",
        status=EnvelopeStatus.FAILED,
        error=ErrorEnvelope(
            code="stt_timeout",
            message="Timed out waiting for STT response",
            retryable=True,
        ),
    )
    client = FakeSTTRuntimeClient(script=[timeout_response])

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            transcribe_audio(
                audio=_audio_file(),
                req=_request_for(FakeRuntimeRegistry(client)),
            )
        )

    assert exc_info.value.status_code == 504
    assert "Timed out" in exc_info.value.detail


def test_stt_restart_smoke_restores_file_transcription():
    """Load, unload, and reload should restore file transcription."""
    from airunner_api.routes.daemon import RuntimeRouteRequest, load_runtime
    from airunner_api.routes.daemon import unload_runtime
    from airunner_api.routes.stt import transcribe_audio

    client = FakeSTTRuntimeClient()
    registry = FakeRuntimeRegistry(client)
    request = _request_for(registry)
    route_request = RuntimeRouteRequest()

    first_load = asyncio.run(load_runtime("stt", route_request, request))
    first_response = asyncio.run(
        transcribe_audio(audio=_audio_file(), req=request)
    )
    unload_response = asyncio.run(
        unload_runtime("stt", route_request, request)
    )
    second_load = asyncio.run(load_runtime("stt", route_request, request))
    second_response = asyncio.run(
        transcribe_audio(audio=_audio_file(), req=request)
    )

    assert first_load.payload["action"] == "load_model"
    assert unload_response.payload["action"] == "unload_model"
    assert second_load.payload["action"] == "load_model"
    assert first_response.text == "runtime transcript"
    assert second_response.text == "runtime transcript"


def test_stt_live_audio_smoke_recovers_after_daemon_failure():
    """Live audio should recover after one daemon-side failure."""
    from airunner.components.stt.workers.audio_processor_worker import (
        AudioProcessorWorker,
    )

    daemon_client = FakeDaemonSTTClient(
        [
            RuntimeError("daemon unavailable"),
            {"text": "recovered transcript"},
        ]
    )
    worker = _worker_for(daemon_client)

    AudioProcessorWorker.handle_message(worker, {"item": b"\x01\x00"})
    AudioProcessorWorker.handle_message(worker, {"item": b"\x02\x00"})

    assert len(daemon_client.calls) == 2
    worker.api.stt.audio_processor_response.assert_called_once_with(
        "recovered transcript"
    )


@pytest.mark.benchmark
def test_stt_runtime_smoke_metrics_are_logged():
    """Capture lightweight file and live-audio latency smoke metrics."""
    from airunner_api.routes.stt import transcribe_audio
    from airunner.components.stt.workers.audio_processor_worker import (
        AudioProcessorWorker,
    )

    route_client = FakeSTTRuntimeClient(delay=0.01)
    worker_client = FakeDaemonSTTClient(
        [
            {"text": "one"},
            {"text": "two"},
            {"text": "three"},
        ],
        delay=0.01,
    )
    worker = _worker_for(worker_client)

    async def invoke_files():
        return await asyncio.gather(
            transcribe_audio(
                audio=_audio_file(),
                req=_request_for(FakeRuntimeRegistry(route_client)),
            ),
            transcribe_audio(
                audio=_audio_file(),
                req=_request_for(FakeRuntimeRegistry(route_client)),
            ),
            transcribe_audio(
                audio=_audio_file(),
                req=_request_for(FakeRuntimeRegistry(route_client)),
            ),
        )

    started = time.perf_counter()
    file_responses = asyncio.run(invoke_files())
    for payload in (b"\x01\x00", b"\x02\x00", b"\x03\x00"):
        AudioProcessorWorker.handle_message(worker, {"item": payload})
    elapsed = max(time.perf_counter() - started, 1e-9)
    total_requests = len(file_responses) + len(worker_client.calls)
    average_latency_ms = (elapsed / total_requests) * 1000
    throughput_rps = total_requests / elapsed

    print(
        "STT runtime smoke metrics: "
        f"file_requests={len(file_responses)} "
        f"live_batches={len(worker_client.calls)} "
        f"avg_latency_ms={average_latency_ms:.2f} "
        f"throughput_rps={throughput_rps:.2f}"
    )