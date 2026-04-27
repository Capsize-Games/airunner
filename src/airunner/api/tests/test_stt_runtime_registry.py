import asyncio
from types import SimpleNamespace

from airunner.ipc.messages import EnvelopeStatus, ResponseEnvelope
from airunner.runtimes.contracts import (
    RuntimeDescriptor,
    RuntimeKind,
    RuntimeMode,
    TransportKind,
)


class FakeSTTRuntimeClient:
    def __init__(self):
        self.requests = []
        self.descriptor = RuntimeDescriptor(
            runtime=RuntimeKind.STT,
            provider="local",
            mode=RuntimeMode.LOCAL_FALLBACK,
            transport=TransportKind.IN_PROCESS,
        )

    def invoke(self, request):
        self.requests.append(request)
        return ResponseEnvelope(
            request_id=request.request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload={"text": "runtime transcript", "language": "en"},
        )


class FakeRegistry:
    def __init__(self, client):
        self.client = client
        self.calls = []

    def resolve(self, runtime, provider, deployment_mode):
        self.calls.append((runtime, provider, deployment_mode))
        return self.client


class FakeUploadFile:
    def __init__(self, filename: str, content_type: str, data: bytes):
        self.filename = filename
        self.content_type = content_type
        self._data = data

    async def read(self):
        return self._data


def test_stt_endpoint_uses_runtime_registry_when_available():
    from airunner.api.routes.stt import transcribe_audio

    client = FakeSTTRuntimeClient()
    registry = FakeRegistry(client)
    fake_request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(runtime_registry=registry),
        )
    )
    audio = FakeUploadFile("clip.wav", "audio/wav", b"fake-audio")

    response = asyncio.run(transcribe_audio(audio=audio, req=fake_request))

    assert response.text == "runtime transcript"
    assert response.language == "en"
    assert registry.calls == [(RuntimeKind.STT, "local", "local_fallback")]
    assert client.requests[0].payload["mime_type"] == "audio/wav"
    assert client.requests[0].runtime == RuntimeKind.STT