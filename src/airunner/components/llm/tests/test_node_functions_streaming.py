"""Tests for streamed thinking persistence in NodeFunctionsMixin."""

from types import SimpleNamespace
from unittest.mock import Mock

from airunner.components.llm.managers.mixins.node_functions_mixin import (
    NodeFunctionsMixin,
)


def _chunk(content: str) -> SimpleNamespace:
    """Return one fake streamed chunk."""
    return SimpleNamespace(
        message=SimpleNamespace(
            content=content,
            additional_kwargs={},
            tool_calls=[],
        )
    )


def _reasoning_chunk(content: str, thinking: str) -> SimpleNamespace:
    """Return one fake streamed chunk with reasoning metadata."""
    return SimpleNamespace(
        message=SimpleNamespace(
            content=content,
            additional_kwargs={"reasoning_content": thinking},
            tool_calls=[],
        )
    )


class NodeFunctionsMixinDouble(NodeFunctionsMixin):
    """Small test double for NodeFunctionsMixin streaming helpers."""

    def __init__(self, chunks):
        """Initialize one fake chat model stream."""
        self._chat_model = SimpleNamespace(
            stream=lambda *_args, **_kwargs: iter(chunks)
        )
        self._current_request_id = "req-1"
        self._interrupted = False
        self._signal_emitter = SimpleNamespace(emit_signal=Mock())
        self._token_callback = Mock()
        self.logger = Mock()

    @staticmethod
    def _is_tool_call_json(_text):
        """Return False for plain text chunks in tests."""
        return False


def test_streaming_response_excludes_thinking_blocks_from_content():
    """Saved streamed content should exclude visible thinking text."""
    thinking = 'Okay, the user said "Hello".'
    mixin = NodeFunctionsMixinDouble(
        [_chunk(f"<think>{thinking}</think>Hello!")]
    )

    message = mixin._generate_streaming_response([], {})

    assert message.content == "Hello!"
    assert message.additional_kwargs["thinking_content"] == thinking
    mixin._token_callback.assert_called_once_with("Hello!")


def test_headless_streaming_persists_visible_text_only():
    """Headless streams should save visible text separately from thinking."""
    thinking = 'Okay, the user said "Hello".'
    mixin = NodeFunctionsMixinDouble(
        [_chunk(f"<think>{thinking}</think>Hello!")]
    )
    mixin._signal_emitter = None

    message = mixin._generate_streaming_response([], {})

    assert message.content == "Hello!"
    assert message.additional_kwargs["thinking_content"] == thinking
    mixin._token_callback.assert_called_once_with(
        f"<think>{thinking}</think>Hello!"
    )


def test_headless_reasoning_deltas_still_persist_thinking_content():
    """Reasoning deltas should be persisted without a GUI emitter."""
    thinking = 'Okay, the user said "Hello".'
    mixin = NodeFunctionsMixinDouble([_reasoning_chunk("Hello!", thinking)])
    mixin._signal_emitter = None

    message = mixin._generate_streaming_response([], {})

    assert message.content == "Hello!"
    assert message.additional_kwargs["thinking_content"] == thinking
    mixin._token_callback.assert_called_once_with("Hello!")