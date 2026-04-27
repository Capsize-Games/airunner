from types import SimpleNamespace

from fastapi.testclient import TestClient

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


def test_stt_endpoint_uses_runtime_registry_when_available(monkeypatch):
    from airunner.api.server import create_app

    monkeypatch.setenv("AIRUNNER_INSECURE_NO_AUTH", "1")

    client = FakeSTTRuntimeClient()
    registry = FakeRegistry(client)
    app_instance = SimpleNamespace(runtime_registry=registry)
    app = create_app(enable_cors=False, app_instance=app_instance)

    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/v1/stt/transcribe",
            files={"audio": ("clip.wav", b"fake-audio", "audio/wav")},
        )

    assert response.status_code == 200
    assert response.json() == {"text": "runtime transcript", "language": "en"}
    assert registry.calls == [(RuntimeKind.STT, "local", "local_fallback")]
    assert client.requests[0].payload["mime_type"] == "audio/wav"
    assert client.requests[0].runtime == RuntimeKind.STT