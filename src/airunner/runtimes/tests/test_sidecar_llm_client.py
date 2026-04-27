"""Tests for the llama.cpp sidecar runtime client."""

import json

from airunner.ipc.messages import EnvelopeStatus, RequestEnvelope
from airunner.runtimes.contracts import (
    ChatMessage,
    MessageRole,
    RuntimeAction,
    RuntimeHealthStatus,
    RuntimeKind,
)
from airunner.runtimes.llama_cpp_runtime_settings import (
    LlamaCppRuntimeSettings,
)
from airunner.runtimes.sidecar_llm_client import SidecarLLMClient


class FakeResponse:
    """Minimal context-managed HTTP response."""

    def __init__(self, *, body: bytes = b"", lines=None):
        self._body = body
        self._lines = iter(lines or [])
        self.status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self._body

    def readline(self):
        try:
            return next(self._lines)
        except StopIteration:
            return b""


class FakeLauncher:
    """Minimal launcher double for sidecar client tests."""

    def __init__(self, settings):
        self.settings = settings
        self.endpoint = settings.endpoint
        self.started = 0
        self.stopped = 0
        self.status = RuntimeHealthStatus.READY
        self.details = "ready"

    def start(self):
        self.started += 1

    def stop(self):
        self.stopped += 1

    def health_status(self):
        return self.status, self.details


def _settings() -> LlamaCppRuntimeSettings:
    return LlamaCppRuntimeSettings(
        executable="llama-server",
        host="127.0.0.1",
        port=8011,
        model_path="/tmp/model.gguf",
        model_id="qwen3-8b",
        n_ctx=4096,
        n_gpu_layers=12,
        startup_timeout_seconds=1.0,
    )


def _request(action: RuntimeAction = RuntimeAction.INVOKE) -> RequestEnvelope:
    return RequestEnvelope(
        request_id="req-1",
        runtime=RuntimeKind.LLM,
        action=action,
        payload={
            "messages": [
                ChatMessage(
                    role=MessageRole.USER,
                    content="Say hello",
                ).model_dump()
            ],
            "temperature": 0.2,
            "max_tokens": 32,
        },
    )


def test_load_model_starts_launcher():
    launcher = FakeLauncher(_settings())
    client = SidecarLLMClient(
        settings=_settings(),
        launcher=launcher,
        http_opener=lambda *args, **kwargs: FakeResponse(),
    )

    response = client.invoke(_request(RuntimeAction.LOAD_MODEL))

    assert launcher.started == 1
    assert response.status is EnvelopeStatus.SUCCEEDED


def test_invoke_wraps_chat_completion_response():
    launcher = FakeLauncher(_settings())
    opened = []

    def fake_opener(request, timeout):
        opened.append(json.loads(request.data.decode("utf-8")))
        return FakeResponse(
            body=json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": "hello",
                                "tool_calls": [],
                            }
                        }
                    ],
                    "usage": {"total_tokens": 7},
                }
            ).encode("utf-8")
        )

    client = SidecarLLMClient(
        settings=_settings(),
        launcher=launcher,
        http_opener=fake_opener,
    )

    response = client.invoke(_request())

    assert launcher.started == 1
    assert opened[0]["messages"][0]["content"] == "Say hello"
    assert response.payload["content"] == "hello"
    assert response.payload["usage"]["total_tokens"] == 7


def test_stream_parses_sse_chunks():
    launcher = FakeLauncher(_settings())
    response = FakeResponse(
        lines=[
            b'data: {"choices":[{"delta":{"content":"Hel"}}]}\n',
            b'data: {"choices":[{"delta":{"content":"lo"},"finish_reason":"stop"}]}\n',
        ]
    )
    client = SidecarLLMClient(
        settings=_settings(),
        launcher=launcher,
        http_opener=lambda *args, **kwargs: response,
    )

    deltas = list(client.stream(_request()))

    assert [delta.delta.get("content", "") for delta in deltas] == ["Hel", "lo"]
    assert deltas[-1].final is True


def test_cancel_stops_launcher():
    launcher = FakeLauncher(_settings())
    client = SidecarLLMClient(
        settings=_settings(),
        launcher=launcher,
        http_opener=lambda *args, **kwargs: FakeResponse(),
    )

    response = client.cancel("req-cancel")

    assert launcher.stopped == 1
    assert response.status is EnvelopeStatus.CANCELLED


def test_healthcheck_reports_launcher_status():
    launcher = FakeLauncher(_settings())
    launcher.status = RuntimeHealthStatus.STARTING
    launcher.details = "starting"
    client = SidecarLLMClient(
        settings=_settings(),
        launcher=launcher,
        http_opener=lambda *args, **kwargs: FakeResponse(),
    )

    health = client.healthcheck()

    assert health.status is RuntimeHealthStatus.STARTING
    assert health.metadata["model_id"] == "qwen3-8b"