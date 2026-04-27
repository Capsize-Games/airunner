"""Tests for the GUI daemon bridge in LLMAPIService."""

from types import SimpleNamespace

from airunner.components.llm.api.llm_services import LLMAPIService
from airunner.components.llm.managers.llm_request import LLMRequest
from airunner.enums import LLMActionType


def test_send_request_via_daemon_starts_background_stream(monkeypatch):
    client = SimpleNamespace(ensure_connected=lambda: True)
    started = {}

    class FakeThread:
        def __init__(self, target, args, daemon):
            started["target"] = target
            started["args"] = args
            started["daemon"] = daemon

        def start(self):
            started["started"] = True

    fake_self = SimpleNamespace(
        _daemon_client=lambda: client,
        _stream_daemon_request=lambda *args: None,
    )

    monkeypatch.setattr(
        "airunner.components.llm.api.llm_services.threading.Thread",
        FakeThread,
    )

    result = LLMAPIService._send_request_via_daemon(
        fake_self,
        "hello",
        LLMRequest(),
        LLMActionType.CHAT,
        "req-123",
        None,
        None,
        None,
        None,
    )

    assert result is True
    assert started["started"] is True
    assert started["daemon"] is True
    assert started["args"][0] is client
    assert started["args"][4] == "req-123"