"""Message-building helpers for GGUF chat generation."""

from __future__ import annotations

from typing import Any, Optional

from langchain_core.messages import AIMessage

from airunner_services.llm.gpt_oss_parser import (
    has_gpt_oss_markup,
    parse_gpt_oss_response,
)


def response_message(adapter: Any, response: dict[str, Any]) -> AIMessage:
    """Build one AIMessage from a llama.cpp response payload."""
    message_data = response["choices"][0].get("message", {})
    content = message_data.get("content", "") or ""
    thinking_content = _thinking_content(adapter, message_data)
    gpt_oss_tool_calls, content, thinking_content = (
        _normalized_response_parts(adapter, content, thinking_content)
    )
    tool_calls, content = _tool_calls_from_message(
        adapter, message_data, content, gpt_oss_tool_calls
    )
    _log_tool_calls(adapter, tool_calls)
    return AIMessage(
        content=content,
        tool_calls=tool_calls,
        additional_kwargs=_response_additional_kwargs(thinking_content),
    )


def _normalized_response_parts(
    adapter: Any,
    content: str,
    thinking_content: Optional[str],
) -> tuple[list[dict[str, Any]], str, Optional[str]]:
    """Return normalized GPT-OSS response parts when markup is present."""
    if not (adapter._uses_gpt_oss_parser() or has_gpt_oss_markup(content)):
        return [], content, thinking_content
    return _parse_gpt_oss_content(adapter, content, thinking_content)


def _log_tool_calls(adapter: Any, tool_calls: list[dict[str, Any]]) -> None:
    """Log parsed tool-call counts when tool calls were found."""
    if tool_calls:
        adapter.logger.debug(
            "[TOOL CALL] Parsed %s tool calls from response",
            len(tool_calls),
        )


def _response_additional_kwargs(
    thinking_content: Optional[str],
) -> dict[str, str]:
    """Build AIMessage additional kwargs for optional reasoning text."""
    if not thinking_content:
        return {}
    return {"thinking_content": thinking_content}


def _thinking_content(adapter: Any, message_data: Any) -> Optional[str]:
    """Return reasoning content from one model message when enabled."""
    if adapter.enable_thinking and hasattr(message_data, "get"):
        return message_data.get("reasoning_content")
    return None


def _parse_gpt_oss_content(
    adapter: Any,
    content: str,
    thinking_content: Optional[str],
) -> tuple[list[dict[str, Any]], str, Optional[str]]:
    """Normalize one GPT-OSS content payload."""
    tool_calls = adapter._parse_gpt_oss_commentary_tool_calls(content)
    parsed = parse_gpt_oss_response(content)
    if not thinking_content:
        thinking_content = parsed.thinking_content
    return tool_calls, parsed.content, thinking_content


def _tool_calls_from_message(
    adapter: Any,
    message_data: Any,
    content: str,
    gpt_oss_tool_calls: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], str]:
    """Return tool calls and cleaned content from one message payload."""
    raw_tool_calls = (
        message_data.get("tool_calls")
        if hasattr(message_data, "get")
        else None
    )
    tool_calls = adapter._parse_native_tool_calls(raw_tool_calls)
    if not tool_calls:
        tool_calls, content = adapter._extract_tool_calls(content)
    if not tool_calls and gpt_oss_tool_calls:
        tool_calls = gpt_oss_tool_calls
    return tool_calls, content