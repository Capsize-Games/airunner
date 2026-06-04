"""Mode-specific response parsers for HuggingFace tool calling."""

from __future__ import annotations

import json
import re
from typing import Any, Optional, Tuple

from airunner_services.llm.adapters.mixins.tool_call_json_parsing import (
    try_parse_embedded_json,
    try_parse_json_blocks,
    try_parse_tool_call_tags,
)
from airunner_services.llm.adapters.mixins.tool_call_payload_helpers import (
    fix_json_quotes,
    try_parse_entire_response,
)
from airunner_services.llm.tool_call_identity import build_tool_call_id


def parse_mistral_tool_calls(
    adapter: Any,
    response_text: str,
) -> Tuple[Optional[list[dict]], str]:
    """Parse tool calls from Mistral native output."""
    tool_calls: list[dict] = []
    tool_call_pattern = r"\[TOOL_CALLS\]\s*(\[.*?\])"
    matches = re.findall(tool_call_pattern, response_text, re.DOTALL)
    for match in matches:
        _append_mistral_calls(tool_calls, match)
    cleaned_text = re.sub(
        tool_call_pattern,
        "",
        response_text,
        flags=re.DOTALL,
    ).strip()
    return tool_calls or None, cleaned_text


def _append_mistral_calls(tool_calls: list[dict], match: str) -> None:
    """Append parsed Mistral tool calls from one matched block."""
    try:
        calls = json.loads(match)
    except json.JSONDecodeError:
        return
    for call in calls:
        if isinstance(call, dict) and "name" in call:
            tool_calls.append(_mistral_tool_call(call))


def _mistral_tool_call(call: dict) -> dict:
    """Normalize one Mistral native tool call."""
    if call.get("id"):
        tool_id = call["id"]
    else:
        args = call.get("arguments", {})
        tool_id = build_tool_call_id(call["name"], args)
    return {
        "name": call["name"],
        "args": call.get("arguments", {}),
        "id": tool_id,
    }


def parse_json_mode_tool_calls(
    adapter: Any,
    response_text: str,
) -> Tuple[Optional[list[dict]], str]:
    """Parse tool calls from structured JSON-mode output."""
    parsed = try_parse_tool_call_tags(adapter, response_text)
    if parsed:
        return parsed
    response_text = fix_json_quotes(response_text)
    parsed = try_parse_entire_response(adapter, response_text)
    if parsed:
        return parsed
    parsed = try_parse_json_blocks(adapter, response_text)
    if parsed:
        return parsed
    parsed = try_parse_embedded_json(adapter, response_text)
    if parsed:
        return parsed
    return None, response_text.strip()