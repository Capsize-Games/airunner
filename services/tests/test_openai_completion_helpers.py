"""Unit tests for the OpenAI completion extraction helpers.

_make_openai_chat_callback and _assemble_openai_completion were
extracted to keep _openai_chat_non_stream within the
long-function threshold. These tests pin the callback filtering
and the completion assembly.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from airunner_services.api.routes.legacy_openai_compat import (
    _assemble_openai_completion,
    _make_openai_chat_callback,
)


def _response(**overrides):
    base = {
        "message": "hi",
        "is_end_of_message": False,
        "is_system_message": False,
        "message_type": "assistant",
        "final_visible_message": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_callback_ignores_missing_response():
    observer = MagicMock()
    callback = _make_openai_chat_callback(observer)
    callback({"response": None})
    observer.publish.assert_not_called()


def test_callback_skips_system_and_thinking():
    observer = MagicMock()
    callback = _make_openai_chat_callback(observer)
    callback({"response": _response(is_system_message=True)})
    callback({"response": _response(message_type="thinking")})
    observer.publish.assert_not_called()


def test_callback_publishes_text():
    observer = MagicMock()
    callback = _make_openai_chat_callback(observer)
    callback({"response": _response(message="hello")})
    observer.publish.assert_called_once()
    kwargs = observer.publish.call_args[1]
    assert kwargs["text"] == "hello"


def test_callback_backend_error_publishes_failed():
    observer = MagicMock()
    callback = _make_openai_chat_callback(observer)
    callback({"response": _response(message_type="error", message="boom")})
    assert observer.publish.call_args[1]["failed"] is True


def test_assemble_basic_completion():
    events = [
        SimpleNamespace(text="a", tools=[], replace_text=False),
        SimpleNamespace(text="b", tools=[], replace_text=False),
    ]
    body = _assemble_openai_completion("m", "r1", events, "prompt", None)
    assert body["model"] == "m"
    assert body["object"] == "chat.completion"
    assert body["choices"][0]["message"]["content"] == "ab"
    assert body["choices"][0]["finish_reason"] == "stop"


def test_assemble_replace_clears_prior():
    events = [
        SimpleNamespace(text="old", tools=[], replace_text=False),
        SimpleNamespace(text="new", tools=[], replace_text=True),
    ]
    body = _assemble_openai_completion("m", "r1", events, "p", None)
    assert body["choices"][0]["message"]["content"] == "new"
