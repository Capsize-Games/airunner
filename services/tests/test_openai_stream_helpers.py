"""Unit tests for the OpenAI stream callback helpers.

_openai_error_frame and _make_openai_stream_callback were extracted
to keep _openai_chat_stream within the long-function threshold.
These tests pin the error messages and the callback's event
filtering, accumulation, and terminal publish behavior.
"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from airunner_services.api.routes.legacy_openai_compat import (
    _make_openai_stream_callback,
    _openai_error_frame,
)


def test_error_frame_timeout():
    payload = json.loads(_openai_error_frame("timeout").decode().split(":", 1)[1])
    assert payload == {"error": {"message": "Request timeout"}}


def test_error_frame_overflow():
    payload = json.loads(_openai_error_frame("overflow").decode().split(":", 1)[1])
    assert payload["error"]["message"] == "Response exceeded the configured output limit"


def test_error_frame_generic():
    payload = json.loads(_openai_error_frame("backend_error").decode().split(":", 1)[1])
    assert payload["error"]["message"] == "LLM generation failed"


def _response(**overrides):
    base = {
        "message": "hi",
        "is_end_of_message": False,
        "is_system_message": False,
        "message_type": "assistant",
        "final_visible_message": None,
    }
    base.update(overrides)
    response = SimpleNamespace(**base)
    response.status = "ok"
    return response


def _callback():
    observer = MagicMock()
    accumulated = []
    callback = _make_openai_stream_callback(
        observer, "m", "r1", None, accumulated
    )
    return callback, observer, accumulated


def test_callback_ignores_none_response():
    callback, observer, accumulated = _callback()
    callback({"response": None})
    observer.publish.assert_not_called()
    assert accumulated == []


def test_callback_skips_system_messages():
    callback, observer, _ = _callback()
    callback({"response": _response(is_system_message=True)})
    observer.publish.assert_not_called()


def test_callback_skips_thinking_events():
    callback, observer, accumulated = _callback()
    callback({"response": _response(message_type="thinking")})
    observer.publish.assert_not_called()
    assert accumulated == []


def test_callback_publishes_content_chunk():
    callback, observer, accumulated = _callback()
    callback({"response": _response(message="hello")})
    assert accumulated == ["hello"]
    observer.publish.assert_called_once()
    kwargs = observer.publish.call_args[1]
    assert kwargs["text"] == "hello"
    assert b"data: " in kwargs["payload"]


def test_callback_terminal_publish_on_end():
    callback, observer, _ = _callback()
    callback({"response": _response(is_end_of_message=True)})
    observer.publish.assert_called_once()
    kwargs = observer.publish.call_args[1]
    assert kwargs["terminal"] is True
    assert kwargs["payload"].endswith(b"data: [DONE]\n\n")
