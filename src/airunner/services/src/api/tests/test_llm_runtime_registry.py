import asyncio
from types import SimpleNamespace

from airunner_services.ipc.messages import EnvelopeStatus, ResponseEnvelope
from airunner.runtimes.contracts import (
    RuntimeDescriptor,
    RuntimeAction,
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
            mode=RuntimeMode.SIDECAR,
            transport=TransportKind.HTTP,
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

    def resolve(self, runtime, provider, deployment_mode="default"):
        self.calls.append((runtime, provider, deployment_mode))
        return self.client


def test_resolve_runtime_registry_reuses_existing_value():
    from airunner_api.server import _resolve_runtime_registry

    runtime_registry = object()
    app_instance = SimpleNamespace(runtime_registry=runtime_registry)

    assert _resolve_runtime_registry(app_instance) is runtime_registry


def test_chat_endpoint_uses_runtime_registry_when_available():
    from airunner_api.routes.llm import ChatCompletionRequest, chat_completion

    client = FakeRuntimeClient()
    registry = FakeRegistry(client)
    request = ChatCompletionRequest(
        messages=[
            {"role": "system", "content": "You are terse."},
            {"role": "user", "content": "Say hello"},
        ],
        temperature=0.25,
        max_tokens=16,
    )
    fake_request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(runtime_registry=registry),
        )
    )

    response = asyncio.run(chat_completion(request, fake_request))

    assert response.content == "runtime hello"
    assert registry.calls == [(RuntimeKind.LLM, "local", "default")]
    payload = client.requests[0].payload
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][1]["content"] == "Say hello"
    assert payload["temperature"] == 0.25
    assert payload["max_tokens"] == 16


def test_load_endpoint_uses_runtime_registry(monkeypatch):
    from airunner_services.api.routes import llm as llm_routes

    client = FakeRuntimeClient()
    registry = FakeRegistry(client)
    fake_request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(runtime_registry=registry),
        )
    )
    persisted = []

    monkeypatch.setattr(
        llm_routes,
        "_persist_model_selection",
        lambda model_id: persisted.append(model_id) or model_id,
    )

    response = asyncio.run(
        llm_routes.load_model(
            llm_routes.ModelLoadRequest(model_id="qwen3-8b"),
            fake_request,
        )
    )

    assert persisted == ["qwen3-8b"]
    assert client.requests[0].action is RuntimeAction.LOAD_MODEL
    assert response == {"status": "success", "model": "qwen3-8b"}