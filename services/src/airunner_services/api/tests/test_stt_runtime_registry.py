import asyncio
from types import SimpleNamespace
from unittest.mock import patch

from airunner_services.ipc.messages import EnvelopeStatus, ResponseEnvelope
from airunner_services.model_management.model_registry import (
    ModelMetadata,
    ModelProvider,
    ModelType,
)
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
            mode=RuntimeMode.SIDECAR,
            transport=TransportKind.HTTP,
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

    def resolve(self, runtime, provider, deployment_mode="default"):
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
    from airunner_api.routes.stt import transcribe_audio

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
    assert registry.calls == [(RuntimeKind.STT, "local", "default")]
    assert client.requests[0].payload["mime_type"] == "audio/wav"
    assert client.requests[0].runtime == RuntimeKind.STT


def test_stt_endpoint_requires_runtime_registry():
    from fastapi import HTTPException

    from airunner_api.routes.stt import transcribe_audio

    fake_request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))
    audio = FakeUploadFile("clip.wav", "audio/wav", b"fake-audio")

    try:
        asyncio.run(transcribe_audio(audio=audio, req=fake_request))
    except HTTPException as exc:
        assert exc.status_code == 503
        assert exc.detail == "STT runtime unavailable"
    else:
        raise AssertionError("Expected HTTPException when runtime is missing")


def test_stt_models_endpoint_filters_speech_to_text_entries():
    from airunner_api.routes.stt import list_models

    fake_registry = SimpleNamespace(
        models={
            "stt-model": ModelMetadata(
                name="Whisper Test",
                provider=ModelProvider.WHISPER,
                model_type=ModelType.SPEECH_TO_TEXT,
                size_gb=1.0,
                min_vram_gb=1.0,
                min_ram_gb=1.0,
                recommended_vram_gb=1.0,
                recommended_ram_gb=1.0,
                supports_quantization=True,
                huggingface_id="whisper/test",
            ),
            "llm-model": ModelMetadata(
                name="LLM Test",
                provider=ModelProvider.LLAMA,
                model_type=ModelType.LLM,
                size_gb=1.0,
                min_vram_gb=1.0,
                min_ram_gb=1.0,
                recommended_vram_gb=1.0,
                recommended_ram_gb=1.0,
                supports_quantization=True,
                huggingface_id="llama/test",
            ),
        }
    )

    with patch(
        "airunner_services.model_management.model_registry.ModelRegistry",
        return_value=fake_registry,
    ):
        response = asyncio.run(list_models(req=SimpleNamespace()))

    assert [model.id for model in response] == ["stt-model"]
    assert response[0].name == "Whisper Test"