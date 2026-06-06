"""LangChain-to-OpenAI tool-call conversion helpers for GGUF."""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional, Sequence


def convert_langchain_tool_calls(
    tool_calls: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Convert LangChain tool call records to OpenAI chat format."""
    converted: List[Dict[str, Any]] = []
    for tool_call in tool_calls or []:
        openai_call = convert_langchain_tool_call(tool_call)
        if openai_call is not None:
            converted.append(openai_call)
    return converted


def convert_langchain_tool_call(
    tool_call: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Convert one LangChain tool call to OpenAI chat format."""
    if not isinstance(tool_call, dict):
        return None
    name = _tool_call_name(tool_call)
    if not name:
        return None
    return {
        "id": tool_call.get("id") or str(uuid.uuid4()),
        "type": "function",
        "function": {
            "name": name,
            "arguments": _tool_call_arguments(tool_call),
        },
    }


def _tool_call_name(tool_call: Dict[str, Any]) -> Any:
    """Return the resolved tool-call name from LangChain payloads."""
    function = tool_call.get("function") or {}
    return tool_call.get("name") or function.get("name")


def _tool_call_arguments(tool_call: Dict[str, Any]) -> str:
    """Return one JSON-encoded argument string for an OpenAI tool call."""
    function = tool_call.get("function") or {}
    arguments = tool_call.get("args", function.get("arguments", {}))
    if isinstance(arguments, str):
        return arguments
    try:
        return json.dumps(arguments or {}, sort_keys=True)
    except TypeError:
        return "{}"
