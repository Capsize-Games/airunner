"""Tests for conversation history citation formatting."""

from __future__ import annotations

from types import SimpleNamespace

from airunner_services.conversation_history_formatter import (
    load_formatted_conversation_history,
)


class _StubLogger:
    """Minimal logger that accepts the formatter's log calls."""

    def debug(self, message: str, *args: object) -> None:
        del message, args

    def info(self, message: str, *args: object) -> None:
        del message, args

    def warning(self, message: str, *args: object) -> None:
        del message, args

    def error(self, message: str, *args: object) -> None:
        del message, args


def _tool_call_message(
    call_id: str = "call_1",
    tool_name: str = "web_search",
    query: str = "python",
) -> dict[str, object]:
    return {
        "metadata_type": "tool_calls",
        "tool_calls": [
            {
                "id": call_id,
                "name": tool_name,
                "args": {"query": query},
            }
        ],
    }


def _tool_result_message(call_id: str, content: str) -> dict[str, object]:
    return {
        "metadata_type": "tool_result",
        "tool_call_id": call_id,
        "content": content,
    }


def _assistant_message(content: str) -> dict[str, object]:
    return {"role": "assistant", "content": content}


def _unexpected_parse(content: str) -> None:
    raise AssertionError(f"unexpected markup parsing for {content}")


def _load_history(
    messages: list[dict[str, object]],
) -> list[dict[str, object]]:
    conversation = SimpleNamespace(
        id=1,
        value=messages,
        chatbot_name="Bot",
        user_name="User",
    )
    return load_formatted_conversation_history(
        logger=_StubLogger(),
        conversation=conversation,
        max_messages=50,
        normalize_thinking_content=lambda value: (
            value if isinstance(value, str) else None
        ),
        strip_stored_thinking_prefix=lambda content, thinking: content,
        has_gpt_oss_markup=lambda content: False,
        parse_gpt_oss_response=_unexpected_parse,
    )


def test_citations_attach_to_following_assistant_message() -> None:
    messages = [
        _tool_call_message(),
        _tool_result_message(
            "call_1",
            "Sources: https://example.com/a and https://example.org/b",
        ),
        _assistant_message("Here are the sources."),
    ]

    history = _load_history(messages)

    assert len(history) == 1
    assert history[0]["citations"] == [
        "https://example.com/a",
        "https://example.org/b",
    ]
    assert history[0]["tool_usage"] == [
        {
            "tool_id": "call_1",
            "tool_name": "web_search",
            "query": "python",
            "details": "example.com, example.org",
        }
    ]


def test_citations_attach_to_synthetic_trailing_message() -> None:
    messages = [
        _tool_call_message(),
        _tool_result_message(
            "call_1",
            "Sources: https://example.com/a and https://example.org/b",
        ),
    ]

    history = _load_history(messages)

    assert len(history) == 1
    synthetic_message = history[0]
    assert synthetic_message["is_bot"] is True
    assert synthetic_message["content"] == ""
    assert synthetic_message["citations"] == [
        "https://example.com/a",
        "https://example.org/b",
    ]
    assert synthetic_message["tool_usage"][0]["tool_id"] == "call_1"


def test_citations_only_create_synthetic_message() -> None:
    history = _load_history(
        [_tool_result_message("call_1", "https://example.com/a")]
    )

    assert len(history) == 1
    assert history[0]["citations"] == ["https://example.com/a"]
    assert "tool_usage" not in history[0]


def test_citations_are_not_duplicated_on_later_assistant_messages() -> None:
    messages = [
        _tool_result_message("call_1", "https://example.com/a"),
        _assistant_message("First answer."),
        _assistant_message("Second answer."),
    ]

    history = _load_history(messages)

    assert len(history) == 2
    assert history[0]["citations"] == ["https://example.com/a"]
    assert "citations" not in history[1]


def test_assistant_message_without_citations_has_no_citation_key() -> None:
    history = _load_history([_assistant_message("Hello")])

    assert history == [
        {
            "name": "Bot",
            "content": "Hello",
            "is_bot": True,
            "id": 0,
        }
    ]
