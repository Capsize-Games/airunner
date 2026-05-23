"""Tests for the runtime-registry-backed STT executor."""

import base64
from types import SimpleNamespace

from airunner_services.ipc.messages import EnvelopeStatus, ResponseEnvelope
from airunner.runtimes.contracts import (
    RuntimeAction,
    RuntimeDescriptor,
    RuntimeKind,
    RuntimeMode,
    TransportKind,
)
from airunner_services.runtimes.runtime_registry_stt_executor import (
    RuntimeRegistrySTTExecutor,
)


class FakeRuntimeClient:
    """Minimal STT runtime client double."""

    def __init__(self, *, fail_invoke: bool = False) -> None:
        self.fail_invoke = fail_invoke
        self.requests = []
        self.descriptor = RuntimeDescriptor(
            runtime=RuntimeKind.STT,
            provider="local",
            mode=RuntimeMode.SIDECAR,
            transport=TransportKind.HTTP,
        )

    def invoke(self, request):
        self.requests.append(request)
        if request.action is RuntimeAction.LOAD_MODEL:
            return ResponseEnvelope(
                request_id=request.request_id,
                status=EnvelopeStatus.SUCCEEDED,
                payload={"action": "load_model"},
            )
        if request.action is RuntimeAction.UNLOAD_MODEL:
            return ResponseEnvelope(
                request_id=request.request_id,
                status=EnvelopeStatus.SUCCEEDED,
                payload={"action": "unload_model"},
            )
        if self.fail_invoke:
            return ResponseEnvelope(
                request_id=request.request_id,
                status=EnvelopeStatus.FAILED,
            )
        return ResponseEnvelope(
            request_id=request.request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload={"text": "runtime transcript", "language": "en"},
        )


def _executor(client: FakeRuntimeClient) -> RuntimeRegistrySTTExecutor:
    registry = SimpleNamespace(resolve=lambda runtime, provider: client)
    api = SimpleNamespace(runtime_registry=registry)
    return RuntimeRegistrySTTExecutor(api=api)


def test_load_invokes_default_stt_runtime() -> None:
    client = FakeRuntimeClient()
    executor = _executor(client)

    assert executor.load() is True
    assert executor.stt_is_loaded is True
    assert client.requests[0].action is RuntimeAction.LOAD_MODEL


def test_transcribe_encodes_audio_for_runtime_request() -> None:
    client = FakeRuntimeClient()
    executor = _executor(client)

    transcription = executor.transcribe(
        {"item": b"\x01\x00", "mime_type": "audio/wav"}
    )

    assert transcription == "runtime transcript"
    assert client.requests[0].action is RuntimeAction.INVOKE
    assert client.requests[0].payload["mime_type"] == "audio/wav"
    assert client.requests[0].payload["audio_b64"] == base64.b64encode(
        b"\x01\x00"
    ).decode("ascii")


def test_transcribe_returns_empty_string_on_runtime_failure() -> None:
    client = FakeRuntimeClient(fail_invoke=True)
    executor = _executor(client)

    transcription = executor.transcribe({"item": b"\x01\x00"})

    assert transcription == ""
    assert executor.stt_is_loaded is False