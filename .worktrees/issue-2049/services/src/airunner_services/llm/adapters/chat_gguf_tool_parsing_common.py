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


def _tool_call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Build one normalized tool-call payload."""
    return {
        "id": str(uuid.uuid4()),
        "name": tool_name,
        "args": arguments,
        "type": "tool_call",
    }