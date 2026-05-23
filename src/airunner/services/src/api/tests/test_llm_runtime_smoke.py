"""Safe smoke tests for the llama.cpp-backed LLM runtime path."""

import asyncio
import threading
import time
from types import SimpleNamespace

import pytest
from fastapi import WebSocketDisconnect

from airunner_services.ipc.messages import (
    EnvelopeStatus,
    ResponseEnvelope,
    StreamDelta,
)
from airunner.runtimes.contracts import (
    RuntimeAction,
    RuntimeDescriptor,
    RuntimeKind,
    RuntimeMode,
    TransportKind,
)
from airunner.runtimes.registry import RuntimeRoute


pytestmark = [
    pytest.mark.llm_runtime_smoke,
    pytest.mark.fast,
]


class FakeLLMRuntimeClient:
    """Thread-safe runtime client double for smoke tests."""

    def __init__(self, delay: float = 0.0, stream_deltas=None) -> None:
        self.delay = delay
        self.stream_deltas = list(stream_deltas or [])
        self.descriptor = RuntimeDescriptor(
            runtime=RuntimeKind.LLM,
            provider="local",
            mode=RuntimeMode.SIDECAR,
            transport=TransportKind.HTTP,
            supports_streaming=True,
        )
        self.invocations = []
        self.stream_requests = []
        self.cancelled_ids = []
        self._lock = threading.Lock()
        self._inflight = 0
        self.max_inflight = 0

    def invoke(self, request):
        """Record a runtime invocation and return a fake response."""
        self.invocations.append(request)
        is_chat = request.action is RuntimeAction.INVOKE
        if is_chat:
            with self._lock:
                self._inflight += 1
                self.max_inflight = max(self.max_inflight, self._inflight)
        try:
            if self.delay:
                time.sleep(self.delay)
            if is_chat:
                messages = request.payload.get("messages", [])
                content = ""
                if messages:
                    content = str(messages[-1].get("content", ""))
                return ResponseEnvelope(
                    request_id=request.request_id,
                    status=EnvelopeStatus.SUCCEEDED,
                    payload={"content": f"echo:{content}"},
                )
            return ResponseEnvelope(
                request_id=request.request_id,
                status=EnvelopeStatus.SUCCEEDED,
                payload={"action": request.action.value},
            )
        finally:
            if is_chat:
                with self._lock:
                    self._inflight -= 1

    def stream(self, envelope):
        """Yield configured stream deltas for websocket tests."""
        self.stream_requests.append(envelope)
        for delta in self.stream_deltas:
            if self.delay:
                time.sleep(self.delay)
            yield delta

    def cancel(self, request_id: str) -> ResponseEnvelope:
        """Record cancellation requests."""
        self.cancelled_ids.append(request_id)
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.CANCELLED,
            metadata={"best_effort": True},
        )


class FakeRuntimeRegistry:
    """Minimal runtime registry double for route tests."""

    def __init__(self, client: FakeLLMRuntimeClient) -> None:
        self.client = client

    def resolve(self, runtime, provider, deployment_mode="default"):
        """Resolve the only supported local LLM runtime."""
        return self.client


class FakeDaemonRegistry:
    """Daemon registry double for cancellation tests."""

    def __init__(self, client: FakeLLMRuntimeClient) -> None:
        self.route_map = {
            RuntimeRoute(RuntimeKind.LLM, provider="local").normalized(): client,
        }

    def list_routes(self):
        """Return registered daemon routes."""
        return tuple(self.route_map.keys())

    def resolve(self, runtime, provider, deployment_mode):
        """Resolve the requested daemon runtime route."""
        route = RuntimeRoute(runtime, provider, deployment_mode).normalized()
        return self.route_map[route]


class FakeWebSocket:
    """WebSocket double for direct websocket route tests."""

    def __init__(self, registry, incoming_messages) -> None:
        self.app = SimpleNamespace(
            state=SimpleNamespace(runtime_registry=registry),
        )
        self._incoming_messages = list(incoming_messages)
        self.accepted = False
        self.sent = []

    async def accept(self) -> None:
        """Accept the websocket connection."""
        self.accepted = True

    async def receive_json(self):
        """Return the next incoming payload or close the socket."""
        if not self._incoming_messages:
            raise WebSocketDisconnect()
        return self._incoming_messages.pop(0)

    async def send_json(self, payload) -> None:
        """Record outbound websocket payloads."""
        self.sent.append(payload)


def _request_for(registry) -> SimpleNamespace:
    """Build a minimal HTTP request double."""
    return SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(runtime_registry=registry))
    )


def _daemon_request_for(registry) -> SimpleNamespace:
    """Build a minimal daemon request double."""
    status = {
        "lifecycle_initialized": True,
        "worker_manager_ready": True,
        "model_load_balancer_ready": True,
        "loaded_models": ["LLM"],
        "runtime_registry_ready": True,
        "embedded_api_server_running": False,
        "preloaded_model_path": None,
    }
    return SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                runtime_registry=registry,
                lifecycle_service=SimpleNamespace(get_status=lambda: status),
            )
        )
    )


def test_llm_runtime_load_and_unload_use_control_actions(monkeypatch):
    """Load and unload should hit the runtime control boundary."""
    from airunner_services.api.routes import llm as llm_routes

    client = FakeLLMRuntimeClient()
    req = _request_for(FakeRuntimeRegistry(client))

    monkeypatch.setattr(
        llm_routes,
        "_persist_model_selection",
        lambda model_id: model_id,
    )

    load_response = asyncio.run(
        llm_routes.load_model(
            llm_routes.ModelLoadRequest(model_id="qwen3-8b"),
            req,
        )
    )
    unload_response = asyncio.run(llm_routes.unload_model(req))

    assert load_response == {"status": "success", "model": "qwen3-8b"}
    assert unload_response == {"status": "success"}
    assert [call.action.value for call in client.invocations[:2]] == [
        "load_model",
        "unload_model",
    ]


@pytest.mark.streaming
def test_llm_websocket_stream_relays_runtime_deltas():
    """The websocket route should forward runtime stream chunks."""
    from airunner_api.routes.llm import websocket_chat

    client = FakeLLMRuntimeClient(
        stream_deltas=[
            StreamDelta(
                request_id="stream-1",
                sequence=0,
                delta={"content": "hello"},
            ),
            StreamDelta(
                request_id="stream-1",
                sequence=1,
                delta={"content": " world"},
                final=True,
            ),
        ]
    )
    websocket = FakeWebSocket(
        FakeRuntimeRegistry(client),
        incoming_messages=[{"message": "Say hello"}],
    )

    asyncio.run(websocket_chat(websocket))

    assert websocket.accepted is True
    assert client.stream_requests[0].stream is True
    assert websocket.sent == [
        {"type": "chunk", "content": "hello", "done": False},
        {"type": "chunk", "content": " world", "done": True},
    ]


def test_llm_runtime_cancel_uses_daemon_cancellation():
    """Cancellation should be delegated to the daemon runtime client."""
    from airunner_api.routes.daemon import RuntimeRouteRequest, cancel_runtime

    client = FakeLLMRuntimeClient()
    req = _daemon_request_for(FakeDaemonRegistry(client))

    response = asyncio.run(
        cancel_runtime(
            "llm",
            RuntimeRouteRequest(request_id="cancel-llm-1"),
            req,
        )
    )

    assert client.cancelled_ids == ["cancel-llm-1"]
    assert response.status is EnvelopeStatus.CANCELLED


def test_llm_runtime_handles_concurrent_chat_requests():
    """Concurrent chat calls should overlap in the runtime boundary."""
    from airunner_api.routes.llm import ChatCompletionRequest, chat_completion

    client = FakeLLMRuntimeClient(delay=0.02)
    req = _request_for(FakeRuntimeRegistry(client))

    async def invoke_all():
        return await asyncio.gather(
            chat_completion(
                ChatCompletionRequest(
                    messages=[{"role": "user", "content": "one"}],
                ),
                req,
            ),
            chat_completion(
                ChatCompletionRequest(
                    messages=[{"role": "user", "content": "two"}],
                ),
                req,
            ),
        )

    responses = asyncio.run(invoke_all())

    assert [response.content for response in responses] == [
        "echo:one",
        "echo:two",
    ]
    assert client.max_inflight >= 2


@pytest.mark.benchmark
def test_llm_runtime_smoke_metrics_are_logged():
    """Capture a lightweight latency and throughput smoke metric."""
    from airunner_api.routes.llm import ChatCompletionRequest, chat_completion

    client = FakeLLMRuntimeClient(delay=0.01)
    req = _request_for(FakeRuntimeRegistry(client))
    request = ChatCompletionRequest(
        messages=[{"role": "user", "content": "metric"}],
    )

    async def invoke_many():
        return await asyncio.gather(
            chat_completion(request, req),
            chat_completion(request, req),
            chat_completion(request, req),
        )

    started = time.perf_counter()
    responses = asyncio.run(invoke_many())
    elapsed = max(time.perf_counter() - started, 1e-9)
    average_latency_ms = (elapsed / len(responses)) * 1000
    throughput_rps = len(responses) / elapsed

    print(
        "LLM runtime smoke metrics: "
        f"requests={len(responses)} "
        f"avg_latency_ms={average_latency_ms:.2f} "
        f"throughput_rps={throughput_rps:.2f}"
    )

    assert all(response.content == "echo:metric" for response in responses)
    assert average_latency_ms > 0
    assert throughput_rps > 0