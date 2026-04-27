from types import SimpleNamespace

from fastapi.testclient import TestClient

from airunner.ipc.messages import EnvelopeStatus, ResponseEnvelope
from airunner.runtimes.contracts import (
    RuntimeDescriptor,
    RuntimeKind,
    RuntimeMode,
    TransportKind,
)


class FakeRuntimeClient:
    def __init__(self):
        self.requests = []
        self.descriptor = RuntimeDescriptor(
            runtime=RuntimeKind.LLM,
            provider="local",
            mode=RuntimeMode.LOCAL_FALLBACK,
            transport=TransportKind.IN_PROCESS,
        )

    def invoke(self, request):
        self.requests.append(request)
        return ResponseEnvelope(
            request_id=request.request_id,
            status=EnvelopeStatus.SUCCEEDED,
            payload={"content": "runtime hello"},
        )


class FakeRegistry:
    def __init__(self, client):
        self.client = client
        self.calls = []

    def resolve(self, runtime, provider, deployment_mode):
        self.calls.append((runtime, provider, deployment_mode))
        return self.client


def test_create_app_reuses_app_instance_runtime_registry():
    from airunner.api.server import create_app

    runtime_registry = object()
    app_instance = SimpleNamespace(runtime_registry=runtime_registry)

    app = create_app(enable_cors=False, app_instance=app_instance)

    assert app.state.runtime_registry is runtime_registry


def test_chat_endpoint_uses_runtime_registry_when_available(monkeypatch):
    from airunner.api.server import create_app

    monkeypatch.setenv("AIRUNNER_INSECURE_NO_AUTH", "1")

    client = FakeRuntimeClient()
    registry = FakeRegistry(client)
    app_instance = SimpleNamespace(runtime_registry=registry)
    app = create_app(enable_cors=False, app_instance=app_instance)

    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/v1/llm/chat",
            json={
                "messages": [
                    {"role": "system", "content": "You are terse."},
                    {"role": "user", "content": "Say hello"},
                ],
                "temperature": 0.25,
                "max_tokens": 16,
            },
        )

    assert response.status_code == 200
    assert response.json()["content"] == "runtime hello"
    assert registry.calls == [(RuntimeKind.LLM, "local", "local_fallback")]
    payload = client.requests[0].payload
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][1]["content"] == "Say hello"
    assert payload["temperature"] == 0.25
    assert payload["max_tokens"] == 16