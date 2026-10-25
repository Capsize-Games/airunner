"""Shared GGUF tool-payload normalization helpers."""

import re
import uuid
from typing import Any, Dict


def normalize_tool_payload(payload: Any) -> Any:
    """Normalize parsed tool payloads before execution."""
    if isinstance(payload, dict):
        return {
            str(key).strip(): normalize_tool_value(str(key), value)
            for key, value in payload.items()
        }
    if isinstance(payload, list):
        return [normalize_tool_payload(item) for item in payload]
    return payload


def normalize_tool_value(key: str, value: Any) -> Any:
    """Normalize one tool payload value recursively.

    ``code`` arguments are passed through byte-for-byte: earlier
    normalization stripped whitespace between digits, silently
    rewriting numeric literals (``range(1, 10)``) and string
    contents inside model-generated code.
    """
    if isinstance(value, (dict, list)):
        return normalize_tool_payload(value)
    if not isinstance(value, str):
        return value
    if key.strip() == "code":
        return value
    cleaned = value.strip()
    if key.strip() in {"tool", "name"}:
        cleaned = re.sub(r"\s*_\s*", "_", cleaned)
        return re.sub(r"\s+", "", cleaned)
    return cleaned


def _tool_call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Build one normalized tool-call payload."""
    return {
        "id": str(uuid.uuid4()),
        "name": tool_name,
        "args": arguments,
        "type": "tool_call",
    }