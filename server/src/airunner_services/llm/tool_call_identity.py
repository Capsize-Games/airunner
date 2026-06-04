"""Shared helpers for deterministic tool-call identity and deduplication."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping


def normalize_tool_call_args(args: Any) -> Any:
    """Return a recursively normalized representation of tool arguments."""
    if isinstance(args, dict):
        return {
            str(key): normalize_tool_call_args(value)
            for key, value in sorted(args.items())
        }
    if isinstance(args, list):
        return [normalize_tool_call_args(value) for value in args]
    if isinstance(args, tuple):
        return [normalize_tool_call_args(value) for value in args]
    return args


def tool_call_argument_string(args: Any) -> str:
    """Return a deterministic serialized representation of tool arguments."""
    normalized_args = normalize_tool_call_args(args)
    try:
        return json.dumps(normalized_args, sort_keys=True)
    except (TypeError, ValueError):
        return repr(normalized_args)


def build_tool_call_id(tool_name: str | None, args: Any) -> str:
    """Return the deterministic tool-call ID for one name/argument pair."""
    arg_string = tool_call_argument_string(args or {})
    content_hash = hashlib.sha256(
        f"{tool_name or ''}:{arg_string}".encode()
    ).hexdigest()[:16]
    return f"tc-{content_hash}"


def tool_call_identity_key(
    tool_call: Mapping[str, Any],
) -> tuple[str, str]:
    """Return the canonical identity key for one tool call payload."""
    tool_name = str(tool_call.get("name") or tool_call.get("tool") or "")
    tool_args = tool_call.get("args")
    if tool_args is None:
        tool_args = tool_call.get("arguments", {})
    return tool_name, tool_call_argument_string(tool_args or {})


def tool_call_identity_set(
    tool_calls: Iterable[Mapping[str, Any]],
) -> set[tuple[str, str]]:
    """Return the canonical identity keys for a collection of tool calls."""
    return {
        tool_call_identity_key(tool_call)
        for tool_call in tool_calls
        if tool_call
    }