"""Tests for the GUI daemon bridge in LLMAPIService."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from airunner.components.llm.api.llm_services import LLMAPIService
from airunner.components.llm.managers.llm_request import LLMRequest
from airunner.enums import LLMActionType, SignalCode


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


def test_send_request_generates_request_id_for_daemon(monkeypatch):
    service = SimpleNamespace(
        logger=MagicMock(),
        emit_signal=MagicMock(),
        _send_request_via_daemon=MagicMock(return_value=True),
    )

    LLMAPIService.send_request(service, "hello", llm_request=LLMRequest())

    call_args = service._send_request_via_daemon.call_args[0]
    assert call_args[0] == "hello"
    assert call_args[3]
    service.emit_signal.assert_not_called()


def test_send_request_with_images_emits_signal_fallback():
    service = SimpleNamespace(
        logger=MagicMock(),
        emit_signal=MagicMock(),
        _send_request_via_daemon=MagicMock(return_value=False),
    )

    llm_request = LLMRequest()
    llm_request.images = [object()]

    LLMAPIService.send_request(service, "vision", llm_request=llm_request)

    service.emit_signal.assert_called_once()
    args, _kwargs = service.emit_signal.call_args
    assert args[0] == SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL
    assert args[1]["request_id"]


def test_send_request_via_daemon_skips_image_requests():
    client = SimpleNamespace(ensure_connected=MagicMock(return_value=True))
    fake_self = SimpleNamespace(_daemon_client=lambda: client)
    llm_request = LLMRequest()
    llm_request.images = [object()]

    result = LLMAPIService._send_request_via_daemon(
        fake_self,
        "vision",
        llm_request,
        LLMActionType.CHAT,
        "req-vision",
        None,
        None,
        None,
        None,
    )

    assert result is False
    client.ensure_connected.assert_not_called()


def test_interrupt_prefers_daemon_client():
    interrupt_llm = MagicMock()
    service = SimpleNamespace(
        _daemon_client=lambda: SimpleNamespace(interrupt_llm=interrupt_llm),
        emit_signal=MagicMock(),
    )

    LLMAPIService.interrupt(service)

    interrupt_llm.assert_called_once_with()
    service.emit_signal.assert_not_called()