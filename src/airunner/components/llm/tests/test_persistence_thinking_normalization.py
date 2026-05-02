"""Regression tests for persisted thinking-content normalization."""

from types import SimpleNamespace
from unittest.mock import Mock

from langchain_core.messages import AIMessage

from airunner.components.conversations.conversation_history_manager import (
    ConversationHistoryManager,
)
from airunner.components.llm.managers.database_chat_message_history import (
    DatabaseChatMessageHistory,
)
from airunner.components.llm.data.conversation import Conversation
from airunner.components.llm.utils.thinking_parser import (
    normalize_thinking_content,
    strip_stored_thinking_prefix,
)


def test_strip_stored_thinking_prefix_handles_compact_content():
    """Visible content should drop a duplicated thinking prefix."""
    thinking = 'Okay, the user said "Hello". I need to respond.'
    content = 'Okay,the user said" Hello".I need to respond.Hello!'

    assert strip_stored_thinking_prefix(content, thinking) == "Hello!"


def test_normalize_thinking_content_ignores_blank_values():
    """Whitespace-only thinking payloads should not render widgets."""
    assert normalize_thinking_content("\n\n") is None


def test_messages_property_strips_legacy_thinking_prefix(monkeypatch):
    """Legacy stored assistant rows should reload without reasoning text."""
    conversation = SimpleNamespace(
        value=[
            {
                "role": "assistant",
                "content": (
                    'Okay,the user said" Hello".I need to respond.Hello!'
                ),
                "thinking_content": (
                    'Okay, the user said "Hello". I need to respond.'
                ),
            }
        ]
    )
    history = DatabaseChatMessageHistory.__new__(DatabaseChatMessageHistory)
    history.ephemeral = False
    history._conversation = conversation
    history.conversation_id = 45
    history.logger = Mock()

    monkeypatch.setattr(Conversation.objects, "get", lambda _conversation_id: conversation)

    messages = history.messages

    assert messages[0].content == "Hello!"
    assert (
        messages[0].additional_kwargs["thinking_content"]
        == 'Okay, the user said "Hello". I need to respond.'
    )


def test_messages_property_normalizes_gpt_oss_channel_content(monkeypatch):
    """Stored Harmony markup should reload into visible content."""
    conversation = SimpleNamespace(
        value=[
            {
                "role": "assistant",
                "content": (
                    "<|channel|>analysis<|message|>"
                    'Okay, the user said "Hello". I need to respond.'
                    "<|end|><|start|>assistant"
                    "<|channel|>final<|message|>"
                    "Hello!<|return|>"
                ),
            }
        ]
    )
    history = DatabaseChatMessageHistory.__new__(DatabaseChatMessageHistory)
    history.ephemeral = False
    history._conversation = conversation
    history.conversation_id = 45
    history.logger = Mock()

    monkeypatch.setattr(
        Conversation.objects,
        "get",
        lambda _conversation_id: conversation,
    )

    messages = history.messages

    assert messages[0].content == "Hello!"
    assert (
        messages[0].additional_kwargs["thinking_content"]
        == 'Okay, the user said "Hello". I need to respond.'
    )


def test_load_conversation_history_strips_legacy_thinking_prefix():
    """Restarted conversation rendering should keep thinking separate."""
    conversation = SimpleNamespace(
        id=45,
        chatbot_name="Computer",
        user_name="User",
        value=[
            {
                "role": "assistant",
                "content": (
                    'Okay,the user said" Hello".I need to respond.Hello!'
                ),
                "thinking_content": (
                    'Okay, the user said "Hello". I need to respond.'
                ),
                "timestamp": "2026-04-30T14:00:00+00:00",
                "blocks": [
                    {
                        "block_type": "text",
                        "text": (
                            'Okay,the user said" Hello".I need '
                            'to respond.Hello!'
                        ),
                    }
                ],
            }
        ],
    )

    messages = ConversationHistoryManager().load_conversation_history(
        conversation=conversation,
    )

    assert messages[0]["content"] == "Hello!"
    assert (
        messages[0]["thinking_content"]
        == 'Okay, the user said "Hello". I need to respond.'
    )


def test_load_conversation_history_normalizes_gpt_oss_channel_content():
    """Restarted GPT-OSS rows should render without Harmony markup."""
    conversation = SimpleNamespace(
        id=45,
        chatbot_name="Computer",
        user_name="User",
        value=[
            {
                "role": "assistant",
                "content": (
                    "<|channel|>analysis<|message|>"
                    'Okay, the user said "Hello". I need to respond.'
                    "<|end|><|start|>assistant"
                    "<|channel|>final<|message|>"
                    "Hello!<|return|>"
                ),
                "timestamp": "2026-04-30T14:00:00+00:00",
                "blocks": [
                    {
                        "block_type": "text",
                        "text": (
                            "<|channel|>analysis<|message|>"
                            'Okay, the user said "Hello". '
                            "I need to respond.<|end|>"
                            "<|start|>assistant"
                            "<|channel|>final<|message|>"
                            "Hello!<|return|>"
                        ),
                    }
                ],
            }
        ],
    )

    messages = ConversationHistoryManager().load_conversation_history(
        conversation=conversation,
    )

    assert messages[0]["content"] == "Hello!"
    assert (
        messages[0]["thinking_content"]
        == 'Okay, the user said "Hello". I need to respond.'
    )