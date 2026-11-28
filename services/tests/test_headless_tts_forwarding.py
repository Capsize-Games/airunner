"""Unit tests for the headless-TTS forwarding helpers.

_headless_tts_gate_allows, _resolve_full_message, and
_dispatch_final_to_tts were extracted to keep
_forward_headless_tts_final_response within the long-function
threshold. These tests pin the gate branches, the buffer cleanup,
and the queue/handler dispatch preference.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from airunner_services.api.services.llm_services import LLMAPIService


def _make_service():
    service = LLMAPIService.__new__(LLMAPIService)
    service._headless_tts_request_enabled = {}
    service._headless_tts_response_buffer = {}
    service._is_headless_tts_assistant_response = MagicMock(return_value=True)
    service._tts_stream_worker = MagicMock(return_value=None)
    return service


def _response(**overrides):
    base = {
        "request_id": "r1",
        "message": "hello",
        "is_end_of_message": True,
        "is_system_message": False,
        "message_type": "assistant",
        "final_visible_message": None,
        "sequence_number": 3,
        "action": None,
        "node_id": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_gate_rejects_non_assistant():
    service = _make_service()
    service._is_headless_tts_assistant_response.return_value = False
    assert not service._headless_tts_gate_allows(_response(), "r1")


def test_gate_rejects_disabled_request_and_cleans_on_end():
    service = _make_service()
    service._headless_tts_request_enabled = {"r1": False}
    service._headless_tts_response_buffer = {"r1": "x"}
    assert not service._headless_tts_gate_allows(_response(), "r1")
    assert service._headless_tts_response_buffer == {}
    assert service._headless_tts_request_enabled == {}


def test_gate_rejects_disabled_request_without_end():
    service = _make_service()
    service._headless_tts_request_enabled = {"r1": False}
    service._headless_tts_response_buffer = {"r1": "x"}
    assert not service._headless_tts_gate_allows(
        _response(is_end_of_message=False), "r1"
    )
    assert service._headless_tts_response_buffer == {"r1": "x"}


def test_gate_allows_enabled_request():
    service = _make_service()
    service._headless_tts_request_enabled = {"r1": True}
    assert service._headless_tts_gate_allows(_response(), "r1")


def test_resolve_prefers_final_visible_message():
    service = _make_service()
    service._headless_tts_response_buffer = {"r1": "buffered"}
    service._headless_tts_request_enabled = {"r1": True}
    full = service._resolve_full_message(
        _response(final_visible_message="final"), "r1"
    )
    assert full == "final"
    assert service._headless_tts_response_buffer == {}
    assert service._headless_tts_request_enabled == {}


def test_resolve_falls_back_to_buffer():
    service = _make_service()
    service._headless_tts_response_buffer = {"r1": "buffered"}
    full = service._resolve_full_message(_response(), "r1")
    assert full == "buffered"


def test_resolve_none_for_system_message():
    service = _make_service()
    service._headless_tts_response_buffer = {"r1": "buffered"}
    assert (
        service._resolve_full_message(_response(is_system_message=True), "r1")
        is None
    )


def test_dispatch_prefers_queue():
    service = _make_service()
    worker = MagicMock()
    service._tts_stream_worker.return_value = worker
    assert service._dispatch_final_to_tts(_response(), "r1", "full") is True
    worker.add_to_queue.assert_called_once_with(
        {"message": "full", "is_end_of_message": True}
    )
    worker.on_llm_text_streamed_signal.assert_not_called()


def test_dispatch_falls_back_to_handler():
    service = _make_service()
    worker = MagicMock()
    del worker.add_to_queue
    service._tts_stream_worker.return_value = worker
    assert service._dispatch_final_to_tts(_response(), "r1", "full") is True
    worker.on_llm_text_streamed_signal.assert_called_once()


def test_dispatch_no_worker_returns_false():
    service = _make_service()
    service._tts_stream_worker.return_value = None
    assert service._dispatch_final_to_tts(_response(), "r1", "full") is False
