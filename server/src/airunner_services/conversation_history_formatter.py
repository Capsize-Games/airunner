"""Shared conversation history formatting helpers."""

from __future__ import annotations

import re
from typing import Any, Callable, Optional

NormalizeThinking = Callable[[Any], Optional[str]]
StripStoredThinking = Callable[[str, Optional[str]], str]
HasMarkup = Callable[[str], bool]
ParseMarkup = Callable[[str], Any]
SkipMessage = Callable[[dict[str, Any]], bool]

_QUERY_KEYS = (
    "query",
    "search_query",
    "prompt",
    "input",
    "question",
)
_URL_PATTERN = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+')


def _extract_query_from_tool_call(tool_call: dict[str, Any]) -> str:
    """Return one user-friendly query string from a tool call."""
    args = tool_call.get("args", {})
    if isinstance(args, dict):
        for key in _QUERY_KEYS:
            if key in args:
                return str(args[key])
        for value in args.values():
            if isinstance(value, str) and value:
                return value
    return ""


def load_formatted_conversation_history(
    *,
    logger: Any,
    conversation: Optional[Any],
    max_messages: int,
    normalize_thinking_content: NormalizeThinking,
    strip_stored_thinking_prefix: StripStoredThinking,
    has_gpt_oss_markup: HasMarkup,
    parse_gpt_oss_response: ParseMarkup,
    skip_message: Optional[SkipMessage] = None,
    include_tool_status_metadata: bool = False,
    include_thinking_metadata: bool = False,
) -> list[dict[str, Any]]:
    """Return formatted conversation history for GUI and service consumers."""
    if conversation is None:
        logger.warning("No conversation found. Returning empty history.")
        return []

    conversation_id = getattr(conversation, "id", None)
    logger.debug(
        "Loading conversation history for ID: %s (max: %s)",
        conversation_id,
        max_messages,
    )
    try:
        raw_messages = getattr(conversation, "value", None)
        if not isinstance(raw_messages, list):
            logger.warning(
                "Conversation %s has invalid message data (not a list): %s",
                conversation_id,
                type(raw_messages),
            )
            return []
        if not raw_messages:
            logger.debug("Conversation %s is empty.", conversation_id)
            return []
        if len(raw_messages) > max_messages:
            raw_messages = raw_messages[-max_messages:]

        pending_citations: list[str] = []
        pending_tool_usage: list[dict[str, Any]] = []
        pending_tool_results: dict[str, str] = {}
        pending_pre_tool_thinking: Optional[str] = None
        formatted_messages: list[dict[str, Any]] = []

        for msg_idx, msg_obj in enumerate(raw_messages):
            if not isinstance(msg_obj, dict):
                logger.warning(
                    "Skipping invalid message object (not a dict) in "
                    "conversation %s: %s",
                    conversation_id,
                    msg_obj,
                )
                continue
            if callable(skip_message) and skip_message(msg_obj):
                logger.debug(
                    "Skipping filtered message in conversation %s",
                    conversation_id,
                )
                continue

            metadata_type = msg_obj.get("metadata_type")
            if metadata_type == "tool_calls":
                tool_calls = msg_obj.get("tool_calls", [])
                tool_status_metadata = msg_obj.get("tool_status_metadata")
                for tool_call in tool_calls:
                    tool_usage = {
                        "tool_id": tool_call.get("id", ""),
                        "tool_name": tool_call.get("name", "unknown"),
                        "query": _extract_query_from_tool_call(tool_call),
                        "details": None,
                    }
                    if include_tool_status_metadata and isinstance(
                        tool_status_metadata,
                        dict,
                    ):
                        tool_usage["metadata"] = tool_status_metadata
                    pending_tool_usage.append(tool_usage)
                pending_pre_tool_thinking = normalize_thinking_content(
                    msg_obj.get("thinking_content")
                )
                if pending_pre_tool_thinking:
                    logger.debug(
                        "Captured pre-tool thinking: %s chars",
                        len(pending_pre_tool_thinking),
                    )
                logger.debug(
                    "Collected %s tool calls for next assistant message",
                    len(tool_calls),
                )
                continue

            if metadata_type == "tool_result":
                content_text = str(msg_obj.get("content", "") or "")
                tool_call_id = str(msg_obj.get("tool_call_id", "") or "")
                urls = _URL_PATTERN.findall(content_text)
                pending_citations.extend(urls)
                if urls:
                    domains = [url.split("/")[2] for url in urls[:3]]
                    details = ", ".join(domains)
                    if tool_call_id:
                        pending_tool_results[tool_call_id] = details
                    for tool_usage in pending_tool_usage:
                        if tool_usage.get("tool_id") == tool_call_id:
                            tool_usage["details"] = details
                logger.debug(
                    "Processed tool result: %s, details: %s",
                    tool_call_id,
                    pending_tool_results.get(tool_call_id),
                )
                continue

            role = msg_obj.get("role")
            if role in ("tool_calls", "tool_result"):
                logger.debug(
                    "Skipping tool call message with role: %s",
                    role,
                )
                continue

            is_bot = role == "assistant"
            post_tool_thinking = normalize_thinking_content(
                msg_obj.get("thinking_content")
            )
            name = _message_name(
                conversation=conversation,
                message=msg_obj,
                is_bot=is_bot,
            )
            content = _message_content(
                logger=logger,
                message=msg_obj,
                index=msg_idx,
            )

            if is_bot:
                if has_gpt_oss_markup(content):
                    parsed = parse_gpt_oss_response(content)
                    content = parsed.content or content
                    parsed_thinking = normalize_thinking_content(
                        parsed.thinking_content
                    )
                    if parsed_thinking and not post_tool_thinking:
                        post_tool_thinking = parsed_thinking
                content = strip_stored_thinking_prefix(
                    content,
                    post_tool_thinking,
                )

            formatted_msg = {
                "name": name,
                "content": content,
                "is_bot": is_bot,
                "id": msg_idx,
            }
            if is_bot:
                if pending_pre_tool_thinking:
                    formatted_msg["pre_tool_thinking"] = (
                        pending_pre_tool_thinking
                    )
                    pending_pre_tool_thinking = None
                if post_tool_thinking:
                    formatted_msg["thinking_content"] = post_tool_thinking
                if include_thinking_metadata and isinstance(
                    msg_obj.get("thinking_metadata"),
                    dict,
                ):
                    formatted_msg["thinking_metadata"] = msg_obj.get(
                        "thinking_metadata"
                    )
            if is_bot and pending_tool_usage:
                formatted_msg["tool_usage"] = pending_tool_usage.copy()
                pending_tool_usage.clear()
            if is_bot and pending_citations:
                pending_citations.clear()
            for key in ("bot_mood", "bot_mood_emoji", "user_mood"):
                if key in msg_obj:
                    formatted_msg[key] = msg_obj[key]
            formatted_messages.append(formatted_msg)

        if pending_tool_usage or pending_pre_tool_thinking:
            logger.info(
                "Creating synthetic assistant message for pending tool "
                "data: %s tools, thinking=%s",
                len(pending_tool_usage),
                pending_pre_tool_thinking is not None,
            )
            synthetic_msg = {
                "name": getattr(conversation, "chatbot_name", None) or "Bot",
                "content": "",
                "is_bot": True,
                "id": len(formatted_messages),
            }
            if pending_pre_tool_thinking:
                synthetic_msg["pre_tool_thinking"] = pending_pre_tool_thinking
            if pending_tool_usage:
                synthetic_msg["tool_usage"] = pending_tool_usage.copy()
            formatted_messages.append(synthetic_msg)

        logger.info(
            "Successfully loaded %s messages for conversation ID: %s",
            len(formatted_messages),
            conversation_id,
        )
        return formatted_messages
    except Exception as exc:
        logger.error(
            "Error loading conversation history for ID %s: %s",
            conversation_id,
            exc,
            exc_info=True,
        )
        return []


def _message_name(
    *,
    conversation: "Conversation",  # noqa: F821
    message: dict[str, Any],
    is_bot: bool,
) -> str:
    """Return the display name for one conversation row."""
    if is_bot:
        return (
            message.get("bot_name")
            or getattr(conversation, "chatbot_name", None)
            or "Bot"
        )
    return (
        message.get("user_name")
        or getattr(conversation, "user_name", None)
        or "User"
    )


def _message_content(
    *,
    logger: Any,
    message: dict[str, Any],
    index: int,
) -> str:
    """Return the text content for one conversation row."""
    content = message.get("content")
    if content is not None:
        logger.debug(
            "Content found directly in message %s: %s...",
            index,
            str(content)[:50],
        )
        return str(content)

    blocks = message.get("blocks")
    if isinstance(blocks, list) and blocks:
        for block in blocks:
            if isinstance(block, dict) and "text" in block:
                content = str(block["text"])
                logger.debug(
                    "Extracted content from blocks: %s...",
                    content[:50],
                )
                return content
        logger.warning("No text found in blocks for message %s", index)
        return ""

    logger.warning("No blocks found for message %s", index)
    return ""
