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


class _ThinkingSensitiveChatModel:
    """Fake model that hides the answer inside thinking unless disabled."""

    def __init__(self):
        self.enable_thinking = True
        self.tools = [{"function": {"name": "rag_search"}}]
        self.tool_choice = {"type": "function", "function": {"name": "rag_search"}}
        self.observed = []

    def stream(self, *_args, **_kwargs):
        self.observed.append(
            {
                "enable_thinking": self.enable_thinking,
                "tools": self.tools,
                "tool_choice": self.tool_choice,
            }
        )
        if self.enable_thinking:
            return iter([_reasoning_chunk("", "draft hidden answer")])
        return iter([_chunk("Visible answer")])


def test_forced_response_stream_disables_thinking_and_tools():
    """Forced synthesis should request a plain visible answer."""
    chat_model = _ThinkingSensitiveChatModel()
    mixin = NodeFunctionsMixinDouble([])
    mixin._chat_model = chat_model

    message = mixin._generate_response_message_from_results(
        "Tool result content",
        "rag_search",
        "What is this document?",
    )

    assert message.content == "Visible answer"
    assert chat_model.observed == [
        {
            "enable_thinking": False,
            "tools": None,
            "tool_choice": None,
        }
    ]
    assert chat_model.enable_thinking is True
    assert chat_model.tools == [{"function": {"name": "rag_search"}}]
    assert chat_model.tool_choice == {
        "type": "function",
        "function": {"name": "rag_search"},
    }


class _ReasoningOnlyChatModel:
    """Fake model that returns only reasoning text for forced synthesis."""

    def __init__(self):
        self.enable_thinking = True
        self.tools = None
        self.tool_choice = None

    def stream(self, *_args, **_kwargs):
        return iter(
            [
                _reasoning_chunk(
                    "",
                    '"I do not have enough information about this document."\n\n'
                    "Thinking Process:\n1. Inspect the request.",
                )
            ]
        )


def test_forced_response_recovers_visible_text_from_reasoning_only_output():
    """Forced synthesis should salvage the first visible paragraph."""
    mixin = NodeFunctionsMixinDouble([])
    mixin._chat_model = _ReasoningOnlyChatModel()

    message = mixin._generate_response_message_from_results(
        "Tool result content",
        "rag_search",
        "What is this document?",
    )

    assert message.content == "I do not have enough information about this document."


class _StructuredReasoningOnlyChatModel:
    """Fake model that returns only structured planning text."""

    def __init__(self):
        self.enable_thinking = True
        self.tools = None
        self.tool_choice = None

    def stream(self, *_args, **_kwargs):
        return iter(
            [
                _reasoning_chunk(
                    "",
                    "Thinking Process:\n\n"
                    "1.  **Analyze the Request:**\n"
                    "    *   Read the prompt.\n\n"
                    "5.  **Refining for Conciseness and Flow:**\n"
                    '    *   "Based on the text provided, this appears to be \'The Ninth Enochian Key\'."\n'
                    '    *   "It serves as a warning against using substances or devices that might cause delusion and enslavement, acting as a protection against false values."\n'
                    '    *   "Additionally, the text describes a ritualistic process where a written message on parchment or paper is burned in a candle flame to send it into the ether, which is mentioned in the context of a Satanic ritual."\n\n'
                    "6.  **Final Review against Constraints:**\n"
                    "    *   Natural and concise.\n",
                )
            ]
        )


def test_forced_response_prefers_drafted_sentences_over_reasoning_headers():
    """Structured reasoning should surface the drafted answer, not the header."""
    mixin = NodeFunctionsMixinDouble([])
    mixin._chat_model = _StructuredReasoningOnlyChatModel()

    message = mixin._generate_response_message_from_results(
        "Tool result content",
        "rag_search",
        "What is this document?",
    )

    assert message.content == (
        "Based on the text provided, this appears to be 'The Ninth Enochian Key'. "
        "It serves as a warning against using substances or devices that might cause delusion and enslavement, acting as a protection against false values. "
        "Additionally, the text describes a ritualistic process where a written message on parchment or paper is burned in a candle flame to send it into the ether, which is mentioned in the context of a Satanic ritual."
    )


class _PromptCapturingChatModel:
    """Fake model that records the forced synthesis prompt."""

    def __init__(self):
        self.enable_thinking = True
        self.tools = None
        self.tool_choice = None
        self.prompts = []

    def stream(self, prompt, *_args, **_kwargs):
        self.prompts.append(prompt[0].content)
        return iter([_chunk("Visible answer")])


def test_forced_response_prompt_prioritizes_document_identity_for_rag():
    """RAG synthesis prompt should prioritize document identity cues."""
    mixin = NodeFunctionsMixinDouble([])
    mixin._chat_model = _PromptCapturingChatModel()

    mixin._generate_response_message_from_results(
        "Matched documents:\nDocument 1: The Satanic Bible - Anton LaVey.pdf",
        "rag_search",
        "What is this document?",
    )

    prompt = mixin._chat_model.prompts[0]
    assert "identify the document first" in prompt
    assert "inferred titles" in prompt
    assert "stored paths" in prompt