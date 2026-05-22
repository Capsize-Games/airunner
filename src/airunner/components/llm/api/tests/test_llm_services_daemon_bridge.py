"""Tests for the GUI daemon bridge in LLMAPIService."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from airunner.components.llm.api.llm_services import LLMAPIService
from airunner.components.llm.managers.llm_request import LLMRequest
from airunner.components.llm.managers.llm_response import LLMResponse
from airunner.daemon_client.daemon_connection_state import (
    DaemonConnectionState,
)
from airunner.enums import LLMActionType, ModelStatus, SignalCode


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


def test_run_daemon_request_prewarms_tts_before_stream():
    prewarm = MagicMock()
    stream = MagicMock()
    worker_manager = SimpleNamespace(
        _start_tts_runtime_prewarm=prewarm,
        application_settings=SimpleNamespace(tts_enabled=False),
    )
    service = SimpleNamespace(
        _worker_manager=lambda: worker_manager,
        _stream_daemon_request=stream,
    )
    client = SimpleNamespace(state=DaemonConnectionState.CONNECTED)
    llm_request = LLMRequest()
    llm_request.do_tts_reply = True

    LLMAPIService._run_daemon_request_or_fallback(
        service,
        client,
        "hello",
        llm_request,
        LLMActionType.CHAT,
        "req-123",
        None,
        None,
        None,
        None,
        None,
    )

    prewarm.assert_called_once_with()
    stream.assert_called_once_with(
        client,
        "hello",
        llm_request,
        LLMActionType.CHAT,
        "req-123",
        None,
        None,
        None,
        None,
    )


def test_run_daemon_request_skips_tts_prewarm_when_disabled():
    prewarm = MagicMock()
    stream = MagicMock()
    worker_manager = SimpleNamespace(
        _start_tts_runtime_prewarm=prewarm,
        application_settings=SimpleNamespace(tts_enabled=False),
    )
    service = SimpleNamespace(
        _worker_manager=lambda: worker_manager,
        _stream_daemon_request=stream,
    )
    client = SimpleNamespace(state=DaemonConnectionState.CONNECTED)
    llm_request = LLMRequest()
    llm_request.do_tts_reply = False

    LLMAPIService._run_daemon_request_or_fallback(
        service,
        client,
        "hello",
        llm_request,
        LLMActionType.CHAT,
        "req-123",
        None,
        None,
        None,
        None,
        None,
    )

    prewarm.assert_not_called()
    stream.assert_called_once_with(
        client,
        "hello",
        llm_request,
        LLMActionType.CHAT,
        "req-123",
        None,
        None,
        None,
        None,
    )


def test_run_daemon_request_prewarms_tts_for_gui_streaming_when_enabled():
    prewarm = MagicMock()
    stream = MagicMock()
    worker_manager = SimpleNamespace(
        _start_tts_runtime_prewarm=prewarm,
        application_settings=SimpleNamespace(tts_enabled=True),
    )
    service = SimpleNamespace(
        _worker_manager=lambda: worker_manager,
        _stream_daemon_request=stream,
    )
    client = SimpleNamespace(state=DaemonConnectionState.CONNECTED)
    llm_request = LLMRequest()
    llm_request.do_tts_reply = False

    LLMAPIService._run_daemon_request_or_fallback(
        service,
        client,
        "hello",
        llm_request,
        LLMActionType.CHAT,
        "req-123",
        None,
        None,
        None,
        None,
        None,
    )

    prewarm.assert_called_once_with()
    stream.assert_called_once_with(
        client,
        "hello",
        llm_request,
        LLMActionType.CHAT,
        "req-123",
        None,
        None,
        None,
        None,
    )


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


def test_unload_prefers_daemon_client(monkeypatch):
    interrupt_llm = MagicMock()
    unload_local_llm = MagicMock()
    started = {}

    class FakeThread:
        def __init__(self, target, args, daemon):
            started["target"] = target
            started["args"] = args
            started["daemon"] = daemon

        def start(self):
            started["started"] = True
            started["target"](*started["args"])

    service = SimpleNamespace(
        _daemon_client=lambda: SimpleNamespace(
            interrupt_llm=interrupt_llm,
            unload_local_llm=unload_local_llm,
        ),
        _emit_local_unload_request=MagicMock(),
    )

    monkeypatch.setattr(
        "airunner.components.llm.api.llm_services.threading.Thread",
        FakeThread,
    )

    LLMAPIService.unload(service, {"source": "widget"})

    assert started["daemon"] is True
    interrupt_llm.assert_called_once_with()
    unload_local_llm.assert_called_once_with(auto_start=False)
    service._emit_local_unload_request.assert_not_called()


def test_unload_prefers_local_worker_when_llm_is_loaded(monkeypatch):
    service = SimpleNamespace(
        _daemon_client=lambda: SimpleNamespace(unload_local_llm=MagicMock()),
        _worker_manager=lambda: SimpleNamespace(
            _llm_generate_worker=SimpleNamespace(
                current_model_status=lambda: ModelStatus.LOADED,
                _pending_llm_request=None,
            )
        ),
        _emit_local_unload_request=MagicMock(),
        _local_llm_should_handle_unload=lambda: LLMAPIService._local_llm_should_handle_unload(service),
    )

    thread_ctor = MagicMock()
    monkeypatch.setattr(
        "airunner.components.llm.api.llm_services.threading.Thread",
        thread_ctor,
    )

    LLMAPIService.unload(service, {"source": "widget"})

    service._emit_local_unload_request.assert_called_once_with(
        {"source": "widget"}
    )
    thread_ctor.assert_not_called()


def test_unload_falls_back_to_local_signals_without_daemon():
    emitted = []
    service = SimpleNamespace(
        _daemon_client=lambda: None,
        emit_signal=lambda code, data=None: emitted.append((code, data)),
        _emit_local_unload_request=lambda payload: LLMAPIService._emit_local_unload_request(
            service,
            payload,
        ),
    )

    LLMAPIService.unload(service, {"source": "widget"})

    assert emitted == [
        (SignalCode.INTERRUPT_PROCESS_SIGNAL, None),
        (SignalCode.LLM_UNLOAD_SIGNAL, {"source": "widget"}),
    ]


def test_send_llm_text_streamed_signal_fast_forwards_to_tts_worker():
    worker = SimpleNamespace(on_llm_text_streamed_signal=MagicMock())
    emitted = []
    service = SimpleNamespace(
        emit_signal=lambda code, data: emitted.append((code, data)),
        _forward_tts_stream_signal=lambda data: LLMAPIService._forward_tts_stream_signal(
            service,
            data,
        ),
        _tts_stream_worker=lambda: worker,
    )
    response = LLMResponse(message="Hello", request_id="req-1")

    LLMAPIService.send_llm_text_streamed_signal(service, response)

    worker.on_llm_text_streamed_signal.assert_called_once()
    assert emitted[0][0] == SignalCode.LLM_TEXT_STREAMED_SIGNAL
    assert emitted[0][1]["_skip_worker_manager_tts"] is True


def test_send_llm_thinking_signal_fast_forwards_to_tts_worker():
    worker = SimpleNamespace(on_llm_thinking_signal=MagicMock())
    emitted = []
    service = SimpleNamespace(
        emit_signal=lambda code, data: emitted.append((code, data)),
        _thinking_signal_payload=lambda status, content, request_id=None: LLMAPIService._thinking_signal_payload(
            service,
            status,
            content,
            request_id,
        ),
        _forward_tts_thinking_signal=lambda data: LLMAPIService._forward_tts_thinking_signal(
            service,
            data,
        ),
        _tts_stream_worker=lambda: worker,
    )

    LLMAPIService.send_llm_thinking_signal(
        service,
        "started",
        "",
        "req-1",
    )

    worker.on_llm_thinking_signal.assert_called_once_with(
        {"status": "started", "content": "", "request_id": "req-1"}
    )
    assert emitted[0][0] == SignalCode.LLM_THINKING_SIGNAL
    assert emitted[0][1]["_skip_worker_manager_tts"] is True


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
    service = _daemon_bridge_service(emitted_responses, emitted_signals)
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


def test_stream_daemon_request_keeps_word_chunks_lossless():
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
    service = _daemon_bridge_service(emitted_responses)
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
        "world",
    ]


def test_response_from_daemon_chunk_preserves_structured_fields():
    response = LLMAPIService._response_from_daemon_chunk(
        {
            "message": "",
            "message_type": "tool_call",
            "thinking_content": "plan",
            "tool_name": "inspect_loaded_documents",
            "tool_arguments": {"query": "what is this document"},
            "tool_status": "started",
        },
        request_id="req-123",
        action=LLMActionType.CHAT,
        node_id=None,
    )

    assert response.message_type == "tool_call"
    assert response.thinking_content == "plan"
    assert response.tool_name == "inspect_loaded_documents"
    assert response.tool_arguments == {
        "query": "what is this document"
    }
    assert response.tool_status == "started"


def test_stream_daemon_request_prefers_structured_tool_call_chunks():
    chunks = [
        {
            "message": "I am calling the search tool.",
            "message_type": "tool_call",
            "tool_name": "rag_search",
            "tool_arguments": {"query": "document title"},
            "is_first_message": True,
            "is_end_of_message": True,
            "sequence_number": 1,
        },
        {
            "message": "This document is a PDF titled Sample.",
            "message_type": "assistant",
            "is_first_message": True,
            "is_end_of_message": True,
            "sequence_number": 2,
        },
    ]
    emitted_responses = []
    service = _daemon_bridge_service(emitted_responses)
    client = SimpleNamespace(
        stream_llm_request=lambda *args, **kwargs: iter(chunks)
    )
    llm_request = LLMRequest()
    llm_request.force_tool = "rag_search"

    LLMAPIService._stream_daemon_request(
        service,
        client,
        "hello",
        llm_request,
        LLMActionType.CHAT,
        "req-123",
        None,
        7,
        None,
        None,
    )

    assert [response.message for response in emitted_responses] == [
        "This document is a PDF titled Sample.",
    ]
    assert emitted_responses[0].message_type == "assistant"


def test_stream_daemon_request_uses_structured_thinking_chunks():
    chunks = [
        {
            "message": "",
            "message_type": "thinking",
            "thinking_content": "plan",
            "is_first_message": True,
            "is_end_of_message": False,
            "sequence_number": 1,
        },
        {
            "message": "Hello",
            "message_type": "assistant",
            "is_first_message": True,
            "is_end_of_message": True,
            "sequence_number": 2,
        },
    ]
    emitted_responses = []
    emitted_signals = []
    service = _daemon_bridge_service(emitted_responses, emitted_signals)
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
    assert [response.message for response in emitted_responses] == ["Hello"]


def _daemon_bridge_service(emitted_responses, emitted_signals=None):
    """Return a daemon-bridge test double with bound helper methods."""
    emitted_signals = emitted_signals if emitted_signals is not None else []
    service = SimpleNamespace()
    service.send_llm_text_streamed_signal = (
        lambda response: emitted_responses.append(response)
    )
    service.send_llm_thinking_signal = (
        lambda status, content, request_id=None: emitted_signals.append(
            (request_id, status, content)
        )
    )
    service._forward_daemon_chunk = lambda chunk, **kwargs: (
        LLMAPIService._forward_daemon_chunk(service, chunk, **kwargs)
    )
    service._forward_structured_daemon_chunk = lambda chunk, **kwargs: (
        LLMAPIService._forward_structured_daemon_chunk(
            service,
            chunk,
            **kwargs,
        )
    )
    service._forward_structured_thinking_chunk = (
        lambda chunk, **kwargs: (
            LLMAPIService._forward_structured_thinking_chunk(
                service,
                chunk,
                **kwargs,
            )
        )
    )
    service._forward_structured_assistant_chunk = (
        lambda chunk, **kwargs: (
            LLMAPIService._forward_structured_assistant_chunk(
                service,
                chunk,
                **kwargs,
            )
        )
    )
    service._extract_visible_daemon_text = (
        lambda message, state, request_id: (
            LLMAPIService._extract_visible_daemon_text(
                service,
                message,
                state,
                request_id=request_id,
            )
        )
    )
    service._finish_daemon_thinking = lambda state, request_id: (
        LLMAPIService._finish_daemon_thinking(
            service,
            state,
            request_id=request_id,
        )
    )
    service._finish_pending_daemon_visible_output = (
        lambda chunk, **kwargs: (
            LLMAPIService._finish_pending_daemon_visible_output(
                service,
                chunk,
                **kwargs,
            )
        )
    )
    service._emit_visible_daemon_parts = lambda visible_parts, **kwargs: (
        LLMAPIService._emit_visible_daemon_parts(
            service,
            visible_parts,
            **kwargs,
        )
    )
    service._build_visible_daemon_response = lambda chunk, **kwargs: (
        LLMAPIService._build_visible_daemon_response(
            service,
            chunk,
            **kwargs,
        )
    )
    service._daemon_message_type = lambda chunk: (
        LLMAPIService._daemon_message_type(chunk)
    )
    service._reset_structured_hidden_output = lambda state: (
        LLMAPIService._reset_structured_hidden_output(state)
    )
    service._response_from_daemon_chunk = lambda chunk, **kwargs: (
        LLMAPIService._response_from_daemon_chunk(chunk, **kwargs)
    )
    service._start_daemon_thinking = lambda state, tag_format, request_id: (
        LLMAPIService._start_daemon_thinking(
            service,
            state,
            tag_format,
            request_id=request_id,
        )
    )
    service._append_daemon_thinking = lambda state, content, request_id: (
        LLMAPIService._append_daemon_thinking(
            service,
            state,
            content,
            request_id=request_id,
        )
    )
    service._daemon_chunk_has_tool_signal = lambda chunk, visible_parts: (
        LLMAPIService._daemon_chunk_has_tool_signal(
            chunk,
            visible_parts,
        )
    )
    return service


def test_stream_daemon_request_hides_force_tool_preamble_stream():
    chunks = [
        {
            "message": (
                "<think>Let me call the rag_search tool to search for "
                "information about documents.</think>"
                "I'm calling the search tool to find information about the "
                "document you're referring to."
            ),
            "is_first_message": True,
            "is_end_of_message": False,
            "sequence_number": 1,
        },
        {
            "message": (
                '{\n  "tool": "rag_search",\n'
                '  "query": "document information title author"\n}'
            ),
            "is_first_message": False,
            "is_end_of_message": True,
            "sequence_number": 2,
        },
        {
            "message": "This document is a PDF titled Sample",
            "is_first_message": True,
            "is_end_of_message": False,
            "sequence_number": 3,
        },
        {
            "message": " by Jane Doe.",
            "is_first_message": False,
            "is_end_of_message": True,
            "sequence_number": 4,
        },
    ]
    emitted_responses = []
    emitted_signals = []
    service = _daemon_bridge_service(emitted_responses, emitted_signals)
    client = SimpleNamespace(
        stream_llm_request=lambda *args, **kwargs: iter(chunks)
    )
    llm_request = LLMRequest()
    llm_request.force_tool = "rag_search"

    LLMAPIService._stream_daemon_request(
        service,
        client,
        "hello",
        llm_request,
        LLMActionType.CHAT,
        "req-123",
        None,
        7,
        None,
        None,
    )

    assert emitted_signals == [
        ("req-123", "started", ""),
        (
            "req-123",
            "streaming",
            "Let me call the rag_search tool to search for "
            "information about documents.",
        ),
        (
            "req-123",
            "completed",
            "Let me call the rag_search tool to search for "
            "information about documents.",
        ),
    ]
    assert [response.message for response in emitted_responses] == [
        "This document is a PDF titled Sample",
        " by Jane Doe.",
    ]
    assert emitted_responses[0].is_first_message is True
    assert emitted_responses[0].sequence_number == 1
    assert emitted_responses[-1].is_end_of_message is True


def test_stream_daemon_request_flushes_force_tool_answer_without_tool_preamble():
    chunks = [
        {
            "message": "This document is a PDF titled Sample.",
            "is_first_message": True,
            "is_end_of_message": True,
            "sequence_number": 1,
        }
    ]
    emitted_responses = []
    service = _daemon_bridge_service(emitted_responses)
    client = SimpleNamespace(
        stream_llm_request=lambda *args, **kwargs: iter(chunks)
    )
    llm_request = LLMRequest()
    llm_request.force_tool = "rag_search"

    LLMAPIService._stream_daemon_request(
        service,
        client,
        "hello",
        llm_request,
        LLMActionType.CHAT,
        "req-123",
        None,
        7,
        None,
        None,
    )

    assert [response.message for response in emitted_responses] == [
        "This document is a PDF titled Sample.",
    ]
    assert emitted_responses[0].is_first_message is True
    assert emitted_responses[0].is_end_of_message is True