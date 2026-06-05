"""GPT-OSS and Harmony tool-parsing helpers for ChatGGUF."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage

from airunner_services.llm.adapters.chat_gguf_tool_parsing_common import (
    _tool_call,
    normalize_tool_payload,
)
from airunner_services.llm.adapters.chat_gguf_tool_parsing_gpt_oss_commentary import (
    parse_gpt_oss_commentary_tool_calls,
)
from airunner_services.llm.gpt_oss_parser import (
    CALL_TOKEN,
    END_TOKEN,
    RETURN_TOKEN,
    looks_like_tool_argument_payload,
    parse_gpt_oss_response,
)


def forced_gpt_oss_tool_name(adapter: Any) -> Optional[str]:
    """Return the forced tool name for raw Harmony prompting."""
    if not adapter._use_raw_gpt_oss_completion():
        return None
    tool_name = _tool_name_from_choice(adapter.tool_choice)
    if not tool_name:
        return None
    available_tools = {
        (tool.get("function", tool) or {}).get("name")
        for tool in adapter.tools or []
    }
    if available_tools and tool_name not in available_tools:
        adapter.logger.warning(
            "Forced GPT-OSS tool %s missing from bound tools %s; "
            "continuing with explicit tool_choice",
            tool_name,
            sorted(name for name in available_tools if name),
        )
    return tool_name


def _tool_name_from_choice(tool_choice: Any) -> Optional[str]:
    """Return the tool name encoded in one tool_choice payload."""
    if isinstance(tool_choice, str):
        normalized = tool_choice.strip()
        if normalized and normalized not in {"auto", "none"}:
            return normalized
    if isinstance(tool_choice, dict):
        function = tool_choice.get("function") or {}
        return function.get("name")
    return None


def build_gpt_oss_message_from_raw(
    adapter: Any,
    raw_text: str,
) -> AIMessage:
    """Normalize one raw Harmony completion into an AIMessage."""
    parsed = parse_gpt_oss_response(raw_text)
    tool_calls, content, suppressed_prefilled_payload = _resolved_raw_tool_calls(
        adapter,
        raw_text,
        parsed.content,
    )
    additional_kwargs = _message_additional_kwargs(
        parsed.thinking_content,
        suppressed_prefilled_payload,
    )
    return AIMessage(
        content=content,
        tool_calls=tool_calls,
        additional_kwargs=additional_kwargs,
    )


def _resolved_raw_tool_calls(
    adapter: Any,
    raw_text: str,
    parsed_content: str,
) -> tuple[list[dict[str, Any]], str, bool]:
    """Return raw Harmony tool calls, fallback text, and suppression state."""
    tool_calls = parse_gpt_oss_commentary_tool_calls(adapter, raw_text)
    if tool_calls:
        return tool_calls, "", False
    tool_calls = parse_prefilled_gpt_oss_tool_call(adapter, raw_text)
    if tool_calls:
        return tool_calls, "", False
    suppressed = _suppressed_prefilled_payload(adapter, raw_text)
    tool_calls, content = adapter._extract_tool_calls(parsed_content or raw_text)
    if suppressed and not tool_calls:
        _log_suppressed_prefilled_payload(adapter)
        return tool_calls, "", True
    return tool_calls, content, suppressed


def _suppressed_prefilled_payload(adapter: Any, raw_text: str) -> bool:
    """Return whether a malformed forced tool payload should be suppressed."""
    return bool(forced_gpt_oss_tool_name(adapter)) and (
        looks_like_tool_argument_payload(raw_text)
    )


def _log_suppressed_prefilled_payload(adapter: Any) -> None:
    """Log when a malformed forced Harmony payload is suppressed."""
    adapter.logger.warning("Suppressing malformed prefilled GPT-OSS tool payload")


def _message_additional_kwargs(
    thinking_content: str,
    suppressed_prefilled_payload: bool,
) -> Dict[str, Any]:
    """Return additional kwargs for one parsed AIMessage."""
    additional_kwargs: Dict[str, Any] = {}
    if thinking_content:
        additional_kwargs["thinking_content"] = thinking_content
    if suppressed_prefilled_payload:
        additional_kwargs["suppressed_malformed_tool_payload"] = True
    return additional_kwargs


def extract_prefilled_gpt_oss_tool_json(content: str) -> str:
    """Return JSON emitted after a prefilled Harmony tool envelope."""
    candidate = (content or "").strip()
    if not candidate:
        return ""
    candidate = _trim_prefilled_markers(candidate)
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", candidate, re.DOTALL)
    if fenced:
        candidate = fenced.group(1).strip()
    if not candidate.startswith("{"):
        return ""
    try:
        _, end_index = json.JSONDecoder().raw_decode(candidate)
    except json.JSONDecodeError:
        return candidate
    return candidate[:end_index].strip()


def _trim_prefilled_markers(candidate: str) -> str:
    """Trim Harmony terminators from a prefilled tool payload."""
    marker_indexes = [
        candidate.find(token)
        for token in (CALL_TOKEN, END_TOKEN, RETURN_TOKEN)
        if token in candidate
    ]
    if marker_indexes:
        return candidate[: min(marker_indexes)].strip()
    return candidate


def parse_prefilled_gpt_oss_tool_call(
    adapter: Any,
    content: str,
) -> List[Dict[str, Any]]:
    """Parse one forced Harmony tool call from a bare JSON body."""
    tool_name = forced_gpt_oss_tool_name(adapter)
    json_text = extract_prefilled_gpt_oss_tool_json(content)
    if not tool_name or not json_text:
        return []
    try:
        arguments = normalize_tool_payload(json.loads(json_text))
    except json.JSONDecodeError as exc:
        adapter.logger.warning(
            "Failed to parse prefilled GPT-OSS tool JSON for %s: %s",
            tool_name,
            exc,
        )
        return []
    if not isinstance(arguments, dict):
        return []
    return [_tool_call(tool_name, arguments)]