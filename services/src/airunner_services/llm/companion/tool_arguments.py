"""Argument adaptation for companion tool calls (B11).

Validates caller-supplied arguments against a registered tool
function's signature before invocation, bridges the B01
``chatbot_id`` scope onto Desktop tool signatures that accept it,
and serializes return values to the dispatch contract's string.
"""

from __future__ import annotations

import inspect
import json
from typing import Any, Callable, Dict, Mapping

from .contracts import ChatbotId


def merge_chatbot_id(
    func: Callable[..., Any],
    arguments: Dict[str, Any],
    chatbot_id: ChatbotId,
) -> Dict[str, Any]:
    """Add ``chatbot_id`` when the tool accepts it and lacks it."""
    merged = dict(arguments)
    if "chatbot_id" in merged:
        return merged
    if _accepts_chatbot_id(func):
        merged["chatbot_id"] = int(chatbot_id)
    return merged


def validate_arguments(
    func: Callable[..., Any],
    arguments: Mapping[str, Any],
) -> bool:
    """Return whether ``arguments`` fit the tool's signature."""
    try:
        params = inspect.signature(func).parameters
    except (TypeError, ValueError):
        return True
    accepts_kwargs = any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()
    )
    if _has_unexpected(params, arguments, accepts_kwargs):
        return False
    return not _has_missing(params, arguments)


def serialize_result(raw: Any) -> str:
    """Serialize one tool return value to the contract's string."""
    if isinstance(raw, str):
        return raw
    return json.dumps(raw, sort_keys=True, default=str)


def _accepts_chatbot_id(func: Callable[..., Any]) -> bool:
    """Return whether the tool takes a ``chatbot_id`` parameter."""
    try:
        params = inspect.signature(func).parameters
    except (TypeError, ValueError):
        return False
    return "chatbot_id" in params or any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()
    )


def _has_unexpected(
    params: Mapping[str, inspect.Parameter],
    arguments: Mapping[str, Any],
    accepts_kwargs: bool,
) -> bool:
    """Return whether any argument fits no declared parameter."""
    return any(key not in params and not accepts_kwargs for key in arguments)


def _has_missing(
    params: Mapping[str, inspect.Parameter],
    arguments: Mapping[str, Any],
) -> bool:
    """Return whether any required parameter has no argument."""
    for name, param in params.items():
        if param.default is not inspect.Parameter.empty:
            continue
        if param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue
        if name not in arguments:
            return True
    return False


__all__ = [
    "merge_chatbot_id",
    "serialize_result",
    "validate_arguments",
]
