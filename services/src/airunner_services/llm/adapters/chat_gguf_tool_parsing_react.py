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
        normalized = _normalize_react_json(raw_input)
        if not normalized:
            continue
        try:
            args = json.loads(normalized)
        except json.JSONDecodeError as error:
            snippet = normalized[:200].replace("\n", " ")
            adapter.logger.error(
                "Failed to parse ReAct JSON for %s: %s | snippet=%s",
                tool_name,
                error,
                snippet,
            )
            continue
        tool_calls.append(
            {
                "name": tool_name,
                "args": args,
                "id": f"call_{len(tool_calls)}",
                "type": "tool_call",
            }
        )
    return tool_calls


def _normalize_react_json(raw_input: str) -> str:
    """Normalize a ReAct Action Input payload into one JSON object."""
    normalized = raw_input.strip().rstrip("</s> ")
    while normalized.startswith("{{") and normalized.endswith("}}"):
        if len(normalized) <= 4:
            break
        normalized = normalized[1:-1]
    while normalized.startswith("{") and normalized.endswith("}}"):
        normalized = normalized[:-1]
    while normalized.startswith("{{") and normalized.endswith("}"):
        normalized = normalized[1:]
    if normalized.startswith("{") and normalized.endswith("}"):
        return normalized
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