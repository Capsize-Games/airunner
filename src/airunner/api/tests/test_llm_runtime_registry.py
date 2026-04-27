import asyncio
from types import SimpleNamespace

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


def test_resolve_runtime_registry_reuses_existing_value():
    from airunner.api.server import _resolve_runtime_registry

    runtime_registry = object()
    app_instance = SimpleNamespace(runtime_registry=runtime_registry)

    assert _resolve_runtime_registry(app_instance) is runtime_registry


def test_chat_endpoint_uses_runtime_registry_when_available():
    from airunner.api.routes.llm import ChatCompletionRequest, chat_completion

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
    assert registry.calls == [(RuntimeKind.LLM, "local", "local_fallback")]
    payload = client.requests[0].payload
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][1]["content"] == "Say hello"
    assert payload["temperature"] == 0.25
    assert payload["max_tokens"] == 16