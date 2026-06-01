"""Payload normalization helpers for HuggingFace tool calling."""

from __future__ import annotations

import ast
import json
import re
from typing import Any, Optional, Tuple

from airunner_services.llm.tool_call_identity import build_tool_call_id


def fix_json_quotes(text: str) -> str:
    """Fix common single-quoted JSON fragments."""
    if "{'tool'" in text or '{"tool":' not in text:
        text_fixed = (
            text.replace("':", '":')
            .replace(": '", ': "')
            .replace("', '", '", "')
            .replace("'}", '"}')
        )
        if text_fixed != text:
            return text_fixed
    return text


def try_parse_entire_response(
    adapter: Any,
    response_text: str,
) -> Optional[Tuple[list[dict], str]]:
    """Try parsing one entire response as tool-call JSON."""
    try:
        data = normalize_tool_payload(json.loads(response_text.strip()))
        if isinstance(data, dict) and is_tool_payload(data):
            return [extract_tool_call(data)], ""
        if isinstance(data, list):
            tool_calls = extract_tool_calls_from_list(data)
            if tool_calls:
                return tool_calls, ""
    except json.JSONDecodeError:
        return try_python_literal_eval(adapter, response_text)
    return None


def try_python_literal_eval(
    adapter: Any,
    response_text: str,
) -> Optional[Tuple[list[dict], str]]:
    """Try parsing one response with `ast.literal_eval`."""
    try:
        data = normalize_tool_payload(ast.literal_eval(response_text.strip()))
        if isinstance(data, dict) and is_tool_payload(data):
            return [extract_tool_call(data)], ""
    except (ValueError, SyntaxError) as error:
        adapter.logger.error(
            "Failed to parse response with literal_eval: %s",
            error,
        )
    return None


def extract_tool_call(data: dict) -> dict:
    """Extract one normalized tool call payload."""
    normalized = normalize_tool_payload(data)
    tool_name = normalized.get("tool") or normalized.get("name")
    tool_args = normalized.get("arguments") or normalized.get("args") or {}
    return {
        "name": tool_name,
        "args": tool_args or {},
        "id": build_tool_call_id(tool_name, tool_args),
    }


def is_tool_payload(data: dict) -> bool:
    """Return whether one normalized dictionary looks like a tool call."""
    if not isinstance(data, dict):
        return False
    return bool(data.get("tool") or data.get("name"))


def normalize_tool_payload(data: Any) -> Any:
    """Normalize spaced keys and string values in parsed tool JSON."""
    if isinstance(data, dict):
        return {
            str(key).strip(): normalize_tool_value(str(key), value)
            for key, value in data.items()
        }
    if isinstance(data, list):
        return [normalize_tool_payload(item) for item in data]
    return data


def normalize_tool_value(key: str, value: Any) -> Any:
    """Normalize one tool payload value recursively."""
    if isinstance(value, (dict, list)):
        return normalize_tool_payload(value)
    if not isinstance(value, str):
        return value
    cleaned = value.strip()
    if key.strip() in {"tool", "name"}:
        cleaned = re.sub(r"\s*_\s*", "_", cleaned)
        return re.sub(r"\s+", "", cleaned)
    if key.strip() == "code":
        return re.sub(r"(?<=\d)\s+(?=\d)", "", cleaned)
    return cleaned


def extract_tool_calls_from_list(data: list[Any]) -> list[dict]:
    """Extract tool calls from one list payload."""
    tool_calls: list[dict] = []
    for item in data:
        normalized = normalize_tool_payload(item)
        if isinstance(normalized, dict) and is_tool_payload(normalized):
            tool_calls.append(extract_tool_call(normalized))
    return tool_calls