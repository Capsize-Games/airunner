"""Tests for the TTS runtime-backed route."""

import asyncio
import base64
from types import SimpleNamespace

from airunner_services.ipc.messages import EnvelopeStatus, ResponseEnvelope
from airunner.runtimes.contracts import (
    RuntimeDescriptor,
    RuntimeKind,
    RuntimeMode,
    TransportKind,
)


class FakeTTSRuntimeClient:
    """Runtime client double for direct TTS route tests."""

    def __init__(self):
        self.descriptor = RuntimeDescriptor(
            runtime=RuntimeKind.TTS,
            provider="local",
            mode=RuntimeMode.SIDECAR,
            transport=TransportKind.HTTP,
            endpoint="http://127.0.0.1:8191",
        )
        self.invocations = []

    def invoke(self, request):
        self.invocations.append(request)
        return ResponseEnvelope(
            request_id=request.request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload={
                "audio_b64": base64.b64encode(b"wav-bytes").decode("ascii"),
            },
        )


class FakeRegistry:
    """Runtime registry double for direct TTS route tests."""

    def __init__(self, client):
        self.client = client

    def resolve(self, runtime, provider, deployment_mode="default"):
        assert runtime is RuntimeKind.TTS
        assert provider == "local"
        assert deployment_mode == "sidecar"
        return self.client


class FakeFallbackRegistry:
    """Runtime registry double that falls back to local TTS."""

    def __init__(self, client):
        self.client = client

    def resolve(self, runtime, provider, deployment_mode="default"):
        assert runtime is RuntimeKind.TTS
        assert provider == "local"
        if deployment_mode == "sidecar":
            raise KeyError("sidecar unavailable")
        assert deployment_mode == "local_fallback"
        return self.client


def _request_for(client):
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(runtime_registry=FakeRegistry(client))))


def _fallback_request_for(client):
    return SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                runtime_registry=FakeFallbackRegistry(client)
            )
        )
    )


def test_synthesize_speech_invokes_sidecar_runtime_client():
    from airunner_api.routes.tts import TTSRequest, synthesize_speech

    client = FakeTTSRuntimeClient()

    async def run_test():
        response = await synthesize_speech(
            TTSRequest(text="Speak this", request_id="tts-route-1"),
            _request_for(client),
        )
        chunk = await response.body_iterator.__anext__()
        return response, chunk

    response, chunk = asyncio.run(run_test())

    assert response.media_type == "audio/wav"
    assert chunk == b"wav-bytes"
    assert client.invocations[0].request_id == "tts-route-1"


def test_synthesize_speech_falls_back_to_local_runtime_client():
    from airunner_api.routes.tts import TTSRequest, synthesize_speech

    client = FakeTTSRuntimeClient()

    async def run_test():
        response = await synthesize_speech(
            TTSRequest(text="Speak this", request_id="tts-route-2"),
            _fallback_request_for(client),
        )
        chunk = await response.body_iterator.__anext__()
        return response, chunk

    response, chunk = asyncio.run(run_test())

    assert response.media_type == "audio/wav"
    assert chunk == b"wav-bytes"
    assert client.invocations[0].request_id == "tts-route-2"