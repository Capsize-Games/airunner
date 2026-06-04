"""ReAct-style tool-parsing helpers for ChatGGUF."""

import json
import re
from typing import Any, Dict, List


def parse_react_tool_calls(
    adapter: Any,
    content: str,
) -> tuple[List[Dict[str, Any]], str]:
    """Parse ReAct tool calls from model response text."""
    react_pattern = (
        r"Action:\s*(\w+)(?:\([^)]*\))?\s*Action Input:\s*"
        r"(.*?)(?=\s*Action:|$)"
    )
    react_matches = re.findall(react_pattern, content, re.DOTALL)
    tool_calls = _react_tool_calls(adapter, react_matches)
    cleaned_text = _clean_react_content(content, react_matches, react_pattern)
    return tool_calls, cleaned_text


def _react_tool_calls(
    adapter: Any,
    react_matches: List[tuple[str, str]],
) -> List[Dict[str, Any]]:
    """Build parsed tool-call payloads from ReAct matches."""
    tool_calls: List[Dict[str, Any]] = []
    for tool_name, raw_input in react_matches:
        tool_call = _react_tool_call(adapter, tool_name, raw_input, len(tool_calls))
        if tool_call is not None:
            tool_calls.append(tool_call)
    return tool_calls


def _react_tool_call(
    adapter: Any,
    tool_name: str,
    raw_input: str,
    index: int,
) -> Dict[str, Any] | None:
    """Return one parsed ReAct tool-call payload when JSON is valid."""
    args = _react_tool_args(adapter, tool_name, raw_input)
    if args is None:
        return None
    return {
        "name": tool_name,
        "args": args,
        "id": f"call_{index}",
        "type": "tool_call",
    }


def _react_tool_args(
    adapter: Any,
    tool_name: str,
    raw_input: str,
) -> Any | None:
    """Parse one ReAct action input into tool-call arguments."""
    normalized = _normalize_react_json(raw_input)
    if not normalized:
        return None
    try:
        return json.loads(normalized)
    except json.JSONDecodeError as error:
        snippet = normalized[:200].replace("\n", " ")
        adapter.logger.error(
            "Failed to parse ReAct JSON for %s: %s | snippet=%s",
            tool_name,
            error,
            snippet,
        )
        return None


def _normalize_react_json(raw_input: str) -> str:
    """Normalize a ReAct Action Input payload into one JSON object."""
    normalized = _trim_react_payload(raw_input)
    normalized = _unwrap_double_braces(normalized)
    normalized = _balance_react_braces(normalized)
    if _is_json_object(normalized):
        return normalized
    return _embedded_json_object(normalized)


def _trim_react_payload(raw_input: str) -> str:
    """Trim trailing stop markers from one ReAct action payload."""
    return raw_input.strip().rstrip("</s> ")


def _unwrap_double_braces(normalized: str) -> str:
    """Remove repeated outer brace pairs from one payload."""
    while len(normalized) > 4:
        if not normalized.startswith("{{") or not normalized.endswith("}}"):
            return normalized
        normalized = normalized[1:-1]
    return normalized


def _balance_react_braces(normalized: str) -> str:
    """Fix one-sided doubled braces around a JSON payload."""
    if normalized.startswith("{") and normalized.endswith("}}"):
        return normalized[:-1]
    if normalized.startswith("{{") and normalized.endswith("}"):
        return normalized[1:]
    return normalized


def _is_json_object(normalized: str) -> bool:
    """Return True when the payload is already a JSON object string."""
    return normalized.startswith("{") and normalized.endswith("}")


def _embedded_json_object(normalized: str) -> str:
    """Extract one embedded JSON object from a larger payload."""
    brace_match = re.search(r"\{.*\}", normalized, re.DOTALL)
    if brace_match:
        return brace_match.group(0).strip()
    return ""


def _clean_react_content(
    content: str,
    react_matches: List[tuple[str, str]],
    react_pattern: str,
) -> str:
    """Remove parsed ReAct tool blocks from one assistant message."""
    if not react_matches:
        return content
    cleaned_text = re.sub(react_pattern, "", content, flags=re.DOTALL).strip()
    return re.sub(
        r"\n?Observation:\s*\[.*?\]",
        "",
        cleaned_text,
        flags=re.DOTALL,
    ).strip()