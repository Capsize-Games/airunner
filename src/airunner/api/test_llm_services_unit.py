"""
Unit tests for LLMAPIService in airunner.api.llm_services.
Covers all public methods and signal emission logic.
"""

import pytest
from unittest.mock import MagicMock
from airunner.api.llm_services import LLMAPIService
from airunner.enums import SignalCode, LLMActionType
from airunner.handlers.llm.llm_request import LLMRequest
from airunner.handlers.llm.llm_response import LLMResponse


@pytest.fixture
def mock_emit_signal():
    return MagicMock()


@pytest.fixture
def llm_service(mock_emit_signal):
    return LLMAPIService(emit_signal=mock_emit_signal)


def test_chatbot_changed_emits_signal(llm_service, mock_emit_signal):
    llm_service.chatbot_changed()
    mock_emit_signal.assert_called_once_with(SignalCode.CHATBOT_CHANGED)


def test_send_request_emits_signal(llm_service, mock_emit_signal):
    prompt = "Hello"
    llm_request = LLMRequest.from_default()
    llm_service.send_request(
        prompt,
        llm_request,
        LLMActionType.CHAT,
        do_tts_reply=False,
        node_id="node1",
    )
    args, kwargs = mock_emit_signal.call_args
    assert args[0] == SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL
    assert args[1]["llm_request"] is True
    assert args[1]["request_data"]["prompt"] == prompt
    assert args[1]["request_data"]["action"] == LLMActionType.CHAT
    assert args[1]["request_data"]["do_tts_reply"] is False
    assert args[1]["node_id"] == "node1"


def test_clear_history_emits_signal(llm_service, mock_emit_signal):
    llm_service.clear_history(foo="bar")
    mock_emit_signal.assert_called_once_with(
        SignalCode.LLM_CLEAR_HISTORY_SIGNAL, {"foo": "bar"}
    )


def test_converation_deleted_emits_signal(llm_service, mock_emit_signal):
    llm_service.converation_deleted(42)
    mock_emit_signal.assert_called_once_with(
        SignalCode.CONVERSATION_DELETED, {"conversation_id": 42}
    )


def test_model_changed_emits_signal(
    llm_service, mock_emit_signal, monkeypatch
):
    monkeypatch.setattr(
        llm_service, "update_llm_generator_settings", MagicMock()
    )
    llm_service.model_changed("openai")
    llm_service.update_llm_generator_settings.assert_called_once_with(
        "model_service", "openai"
    )
    mock_emit_signal.assert_called_once_with(
        SignalCode.LLM_MODEL_CHANGED, {"model_service": "openai"}
    )


def test_reload_rag_emits_signal(llm_service, mock_emit_signal):
    llm_service.reload_rag(["file1.txt"])
    mock_emit_signal.assert_called_once_with(
        SignalCode.RAG_RELOAD_INDEX_SIGNAL, {"target_files": ["file1.txt"]}
    )
    mock_emit_signal.reset_mock()
    llm_service.reload_rag()
    mock_emit_signal.assert_called_once_with(
        SignalCode.RAG_RELOAD_INDEX_SIGNAL, None
    )


def test_load_conversation_emits_signal(llm_service, mock_emit_signal):
    llm_service.load_conversation(7)
    mock_emit_signal.assert_called_once_with(
        SignalCode.QUEUE_LOAD_CONVERSATION,
        {"action": "load_conversation", "index": 7},
    )


def test_interrupt_emits_signal(llm_service, mock_emit_signal):
    llm_service.interrupt()
    mock_emit_signal.assert_called_once_with(
        SignalCode.INTERRUPT_PROCESS_SIGNAL
    )


def test_delete_messages_after_id_emits_signal(llm_service, mock_emit_signal):
    llm_service.delete_messages_after_id(123)
    mock_emit_signal.assert_called_once_with(
        SignalCode.DELETE_MESSAGES_AFTER_ID, {"message_id": 123}
    )


def test_send_llm_text_streamed_signal_emits_signal(
    llm_service, mock_emit_signal
):
    response = LLMResponse(message="foo")
    llm_service.send_llm_text_streamed_signal(response)
    mock_emit_signal.assert_called_once_with(
        SignalCode.LLM_TEXT_STREAMED_SIGNAL, {"response": response}
    )
