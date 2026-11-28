"""Unit tests for the Ollama non-streaming extraction helpers.

_make_ollama_chat_callback and _assemble_ollama_completion were
extracted to keep _ollama_chat_non_stream within the
long-function threshold. These tests pin the callback filtering
and the completion assembly rules.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from airunner_services.api.routes.legacy_ollama_compat import (
    _assemble_ollama_completion,
    _make_ollama_chat_callback,
)


def _response(**overrides):
    base = {
        "message": "hi",
        "is_end_of_message": False,
        "is_system_message": False,
        "message_type": "assistant",
        "final_visible_message": None,
        "tool_calls": [],
        "usage": {"prompt_tokens": 1},
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _callback():
    observer = MagicMock()
    final_usage = [None]
    callback = _make_ollama_chat_callback(observer, final_usage)
    return callback, observer, final_usage


def test_callback_ignores_missing_response():
    callback, observer, _ = _callback()
    callback({"response": None})
    observer.publish.assert_not_called()


def test_callback_skips_system_and_thinking():
    callback, observer, _ = _callback()
    callback({"response": _response(is_system_message=True)})
    callback({"response": _response(message_type="thinking")})
    observer.publish.assert_not_called()


def test_callback_publishes_text():
    callback, observer, _ = _callback()
    callback({"response": _response(message="hello")})
    observer.publish.assert_called_once()
    kwargs = observer.publish.call_args[1]
    assert kwargs["text"] == "hello"
    assert kwargs["terminal"] is False


def test_callback_final_visible_replaces():
    callback, observer, _ = _callback()
    callback(
        {"response": _response(message="partial", final_visible_message="full")}
    )
    kwargs = observer.publish.call_args[1]
    assert kwargs["text"] == "full"
    assert kwargs["replace_text"] is True


def test_callback_end_of_message_captures_usage():
    callback, observer, final_usage = _callback()
    callback(
        {
            "response": _response(
                is_end_of_message=True,
                prompt_tokens=5,
                completion_tokens=2,
                total_tokens=7,
            )
        }
    )
    assert final_usage[0] == {
        "prompt_tokens": 5,
        "completion_tokens": 2,
        "total_tokens": 7,
    }
    assert observer.publish.call_args[1]["terminal"] is True


def test_assemble_joins_text_in_order():
    events = [
        SimpleNamespace(text="a", tools=[], replace_text=False),
        SimpleNamespace(text="b", tools=[], replace_text=False),
    ]
    body = _assemble_ollama_completion("m", events, 0.0, [None])
    assert body["message"] == {"role": "assistant", "content": "ab"}
    assert body["model"] == "m"
    assert body["done"] is True


def test_assemble_replace_clears_prior_text():
    events = [
        SimpleNamespace(text="old", tools=[], replace_text=False),
        SimpleNamespace(text="new", tools=[], replace_text=True),
    ]
    body = _assemble_ollama_completion("m", events, 0.0, [None])
    assert body["message"]["content"] == "new"


def test_assemble_tool_calls_clear_content():
    events = [
        SimpleNamespace(text="ignored", tools=["tc1"], replace_text=False),
    ]
    body = _assemble_ollama_completion("m", events, 0.0, [None])
    assert body["message"] == {
        "role": "assistant",
        "content": "",
        "tool_calls": ["tc1"],
    }
