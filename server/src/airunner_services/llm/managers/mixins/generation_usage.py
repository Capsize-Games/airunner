"""Usage-token extraction helpers for LLM generation responses."""

from __future__ import annotations

from typing import Any, Optional

from langchain_core.messages import AIMessage


def extract_usage_tokens(
    result: dict[str, Any],
) -> tuple[Optional[int], Optional[int], Optional[int]]:
    """Best-effort extract provider token usage from one result."""
    try:
        last_msg = _last_message(result)
        if last_msg is None:
            return None, None, None
        return _usage_from_message(last_msg)
    except Exception:
        return None, None, None


def executed_tools_from_workflow(workflow_manager) -> list[str]:
    """Return the executed tools reported by one workflow manager."""
    if not hasattr(workflow_manager, "get_executed_tools"):
        return []
    raw_executed_tools = workflow_manager.get_executed_tools()
    if isinstance(raw_executed_tools, (list, tuple, set)):
        return list(raw_executed_tools)
    return []


def _last_message(result: dict[str, Any]):
    """Return the final message object from one result when present."""
    messages = result.get("messages") if isinstance(result, dict) else None
    if isinstance(messages, list) and messages:
        return messages[-1]
    return None


def _extract_usage_metadata(
    last_msg: AIMessage,
) -> tuple[Optional[int], Optional[int], Optional[int]]:
    """Extract token counts from usage_metadata attribute."""
    usage = getattr(last_msg, "usage_metadata", None)
    if not isinstance(usage, dict):
        return None, None, None
    return (
        usage.get("input_tokens") or usage.get("prompt_tokens"),
        usage.get("output_tokens") or usage.get("completion_tokens"),
        usage.get("total_tokens"),
    )


def _usage_from_message(
    last_msg: AIMessage,
) -> tuple[Optional[int], Optional[int], Optional[int]]:
    """Return extracted usage counts from one provider message."""
    prompt_t, comp_t, total_t = _extract_usage_metadata(last_msg)
    if prompt_t is None or comp_t is None:
        prompt_t, comp_t, total_t = _usage_from_response_metadata(
            last_msg,
            prompt_t,
            comp_t,
            total_t,
        )
    if total_t is None and (prompt_t is not None or comp_t is not None):
        total_t = int(prompt_t or 0) + int(comp_t or 0)
    return _int_or_none(prompt_t), _int_or_none(comp_t), _int_or_none(total_t)


def _usage_from_response_metadata(
    last_msg: AIMessage,
    prompt_tokens: Optional[int],
    completion_tokens: Optional[int],
    total_tokens: Optional[int],
):
    """Return usage counts extracted from response metadata."""
    response_metadata = getattr(last_msg, "response_metadata", None)
    if not isinstance(response_metadata, dict):
        return prompt_tokens, completion_tokens, total_tokens
    token_usage = response_metadata.get(
        "token_usage"
    ) or response_metadata.get("usage")
    if not isinstance(token_usage, dict):
        return prompt_tokens, completion_tokens, total_tokens
    prompt_tokens = prompt_tokens or token_usage.get("prompt_tokens")
    completion_tokens = completion_tokens or token_usage.get(
        "completion_tokens"
    )
    total_tokens = total_tokens or token_usage.get("total_tokens")
    return prompt_tokens, completion_tokens, total_tokens


def _int_or_none(value: Optional[int]) -> Optional[int]:
    """Return one integer value or None."""
    if value is None:
        return None
    return int(value)
