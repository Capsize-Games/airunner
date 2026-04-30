"""Tests for the GUI daemon bridge in LLMAPIService."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from airunner.components.llm.api.llm_services import LLMAPIService
from airunner.components.llm.managers.llm_request import LLMRequest
from airunner.components.llm.managers.llm_response import LLMResponse
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


def test_stream_daemon_request_converts_thinking_to_ui_signal():
    chunks = [
        {
            "message": "<think>",
            "is_first_message": True,
            "is_end_of_message": False,
            "sequence_number": 1,
        },
        {
            "message": "plan",
            "is_first_message": False,
            "is_end_of_message": False,
            "sequence_number": 2,
        },
        {
            "message": "</think>Hello",
            "is_first_message": False,
            "is_end_of_message": False,
            "sequence_number": 3,
        },
        {
            "message": " world",
            "is_first_message": False,
            "is_end_of_message": False,
            "sequence_number": 4,
        },
        {
            "message": "",
            "is_first_message": False,
            "is_end_of_message": True,
            "sequence_number": 5,
        },
    ]
    emitted_responses = []
    emitted_signals = []
    service = SimpleNamespace(
        send_llm_text_streamed_signal=lambda response: emitted_responses.append(
            response
        ),
        send_llm_thinking_signal=lambda status, content: emitted_signals.append(
            (status, content)
        ),
        _extract_visible_daemon_text=(
            lambda message, state: LLMAPIService._extract_visible_daemon_text(
                service,
                message,
                state,
            )
        ),
        _finish_daemon_thinking=lambda state: (
            LLMAPIService._finish_daemon_thinking(service, state)
        ),
        _emit_visible_daemon_parts=(
            lambda visible_parts, **kwargs: (
                LLMAPIService._emit_visible_daemon_parts(
                    service,
                    visible_parts,
                    **kwargs,
                )
            )
        ),
        _build_visible_daemon_response=(
            lambda chunk, **kwargs: LLMAPIService._build_visible_daemon_response(
                service,
                chunk,
                **kwargs,
            )
        ),
        _response_from_daemon_chunk=(
            lambda chunk, **kwargs: LLMAPIService._response_from_daemon_chunk(
                chunk,
                **kwargs,
            )
        ),
        _start_daemon_thinking=lambda state, tag_format: (
            LLMAPIService._start_daemon_thinking(
                service,
                state,
                tag_format,
            )
        ),
        _append_daemon_thinking=lambda state, content: (
            LLMAPIService._append_daemon_thinking(
                service,
                state,
                content,
            )
        ),
    )
    client = SimpleNamespace(
        stream_llm_request=lambda *args, **kwargs: iter(chunks)
    )

    LLMAPIService._stream_daemon_request(
        service,
        client,
        "hello",
        LLMRequest(),
        LLMActionType.CHAT,
        "req-123",
        None,
        7,
        None,
        None,
    )

    assert emitted_signals == [
        ("started", ""),
        ("streaming", "plan"),
        ("completed", "plan"),
    ]
    assert [response.message for response in emitted_responses] == [
        "Hello",
        " world",
        "",
    ]
    assert [response.sequence_number for response in emitted_responses] == [
        1,
        2,
        3,
    ]
    assert emitted_responses[0].is_first_message is True
    assert emitted_responses[-1].is_end_of_message is True


def test_stream_daemon_request_preserves_error_chunks():
    emitted_responses = []
    service = SimpleNamespace(
        send_llm_text_streamed_signal=lambda response: emitted_responses.append(
            response
        ),
        _build_visible_daemon_response=(
            lambda chunk, **kwargs: LLMAPIService._build_visible_daemon_response(
                service,
                chunk,
                **kwargs,
            )
        ),
        _response_from_daemon_chunk=(
            lambda chunk, **kwargs: LLMAPIService._response_from_daemon_chunk(
                chunk,
                **kwargs,
            )
        ),
    )

    LLMAPIService._forward_daemon_chunk(
        service,
        {
            "message": "Error invoking LLM",
            "error": True,
            "is_end_of_message": True,
            "sequence_number": 0,
        },
        state=SimpleNamespace(visible_sequence_number=0),
        request_id="req-err",
        action=LLMActionType.CHAT,
        node_id=None,
    )

    assert len(emitted_responses) == 1
    assert isinstance(emitted_responses[0], LLMResponse)
    assert emitted_responses[0].message == "Error invoking LLM"
    assert emitted_responses[0].is_system_message is True