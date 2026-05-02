"""Tests for the GUI daemon bridge in LLMAPIService."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from airunner.components.llm.api.llm_services import LLMAPIService
from airunner.components.llm.managers.llm_request import LLMRequest
from airunner.components.llm.managers.llm_response import LLMResponse
from airunner.daemon_client.daemon_connection_state import (
    DaemonConnectionState,
)
from airunner.enums import LLMActionType, SignalCode


def test_send_request_via_daemon_starts_background_stream(monkeypatch):
    client = SimpleNamespace(ensure_connected=lambda **_kwargs: True)
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
    assert started["args"][0] is fake_self
    assert started["args"][1] is client
    assert started["args"][5] == "req-123"


def test_send_request_via_daemon_falls_back_to_local_signal(monkeypatch):
    emitted = []
    client = SimpleNamespace(is_available=MagicMock(return_value=False))

    class FakeThread:
        def __init__(self, target, args, daemon):
            self._target = target
            self._args = args

        def start(self):
            self._target(*self._args)

    service = SimpleNamespace(
        logger=MagicMock(),
        emit_signal=lambda code, data: emitted.append((code, data)),
        _daemon_client=lambda: client,
        _stream_daemon_request=MagicMock(),
    )
    signal_data = {"request_id": "req-123", "request_data": {}}

    monkeypatch.setattr(
        "airunner.components.llm.api.llm_services.threading.Thread",
        FakeThread,
    )

    result = LLMAPIService._send_request_via_daemon(
        service,
        "hello",
        LLMRequest(),
        LLMActionType.CHAT,
        "req-123",
        None,
        None,
        None,
        None,
        signal_data=signal_data,
    )

    assert result is True
    client.is_available.assert_called_once_with(timeout_seconds=0.2)
    assert emitted == [
        (SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL, signal_data)
    ]
    service._stream_daemon_request.assert_not_called()


def test_daemon_client_uses_refreshed_api_reference():
    live_client = object()
    live_api = SimpleNamespace(daemon_client=live_client, headless=False)
    service = SimpleNamespace(
        api=SimpleNamespace(headless=False),
        refresh_api_reference=MagicMock(return_value=live_api),
    )

    client = LLMAPIService._daemon_client(service)

    assert client is live_client
    assert service.api is live_api


def test_immediate_daemon_availability_prefers_connected_state():
    client = SimpleNamespace(
        state=DaemonConnectionState.CONNECTED,
        is_available=MagicMock(return_value=False),
    )

    assert LLMAPIService._daemon_is_immediately_available(object(), client)
    client.is_available.assert_not_called()


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
        send_llm_thinking_signal=lambda status, content, request_id=None: emitted_signals.append(
            (request_id, status, content)
        ),
        _forward_daemon_chunk=(
            lambda chunk, **kwargs: LLMAPIService._forward_daemon_chunk(
                service,
                chunk,
                **kwargs,
            )
        ),
        _extract_visible_daemon_text=(
            lambda message, state, request_id: LLMAPIService._extract_visible_daemon_text(
                service,
                message,
                state,
                request_id=request_id,
            )
        ),
        _finish_daemon_thinking=lambda state, request_id: (
            LLMAPIService._finish_daemon_thinking(
                service,
                state,
                request_id=request_id,
            )
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
        _start_daemon_thinking=lambda state, tag_format, request_id: (
            LLMAPIService._start_daemon_thinking(
                service,
                state,
                tag_format,
                request_id=request_id,
            )
        ),
        _append_daemon_thinking=lambda state, content, request_id: (
            LLMAPIService._append_daemon_thinking(
                service,
                state,
                content,
                request_id=request_id,
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
        ("req-123", "started", ""),
        ("req-123", "streaming", "plan"),
        ("req-123", "completed", "plan"),
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


def test_stream_daemon_request_inserts_spaces_between_word_chunks():
    chunks = [
        {
            "message": "Hello",
            "is_first_message": True,
            "is_end_of_message": False,
            "sequence_number": 1,
        },
        {
            "message": "world",
            "is_first_message": False,
            "is_end_of_message": True,
            "sequence_number": 2,
        },
    ]
    emitted_responses = []
    service = SimpleNamespace(
        send_llm_text_streamed_signal=lambda response: emitted_responses.append(
            response
        ),
        send_llm_thinking_signal=lambda status, content, request_id=None: None,
        _forward_daemon_chunk=(
            lambda chunk, **kwargs: LLMAPIService._forward_daemon_chunk(
                service,
                chunk,
                **kwargs,
            )
        ),
        _extract_visible_daemon_text=(
            lambda message, state, request_id: LLMAPIService._extract_visible_daemon_text(
                service,
                message,
                state,
                request_id=request_id,
            )
        ),
        _finish_daemon_thinking=lambda state, request_id: (
            LLMAPIService._finish_daemon_thinking(
                service,
                state,
                request_id=request_id,
            )
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
        _start_daemon_thinking=lambda state, tag_format, request_id: (
            LLMAPIService._start_daemon_thinking(
                service,
                state,
                tag_format,
                request_id=request_id,
            )
        ),
        _append_daemon_thinking=lambda state, content, request_id: (
            LLMAPIService._append_daemon_thinking(
                service,
                state,
                content,
                request_id=request_id,
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

    assert [response.message for response in emitted_responses] == [
        "Hello",
        " world",
    ]