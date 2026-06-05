"""Harmony commentary tool-call parsing helpers for GPT-OSS GGUF."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from airunner_services.llm.adapters.chat_gguf_tool_parsing_common import (
    _tool_call,
)


def parse_gpt_oss_commentary_tool_calls(
    adapter: Any,
    content: str,
) -> List[Dict[str, Any]]:
    """Parse GPT-OSS Harmony commentary tool calls from raw output."""
    tool_calls: List[Dict[str, Any]] = []
    for match in _commentary_matches(content):
        tool_call = _commentary_tool_call(adapter, match)
        if tool_call is not None:
            tool_calls.append(tool_call)
    return tool_calls


def _commentary_matches(content: str) -> list[re.Match[str]]:
    """Return commentary-channel matches from one Harmony transcript."""
    pattern = re.compile(
        r"(?:<\|start\|>assistant(?P<role_header>[^<]*))?"
        r"<\|channel\|>(?P<channel_header>[^<]*)"
        r"(?:<\|constrain\|>(?P<constraint>[^<]*))?"
        r"<\|message\|>(?P<body>.*?)(?P<terminator><\|call\|>|"
        r"<\|end\|>|<\|return\|>|$)",
        re.DOTALL,
    )
    return list(pattern.finditer(content or ""))


def _commentary_tool_call(
    adapter: Any,
    match: re.Match[str],
) -> Optional[Dict[str, Any]]:
    """Build one tool call from one commentary match when valid."""
    recipient = _commentary_recipient(match)
    if not _is_functions_recipient(recipient):
        return None
    body = (match.group("body") or "").strip()
    if not body:
        return None
    arguments = _load_tool_arguments(adapter, recipient, body)
    if arguments is None:
        return None
    return _tool_call(recipient.removeprefix("functions."), arguments)


def _commentary_recipient(match: re.Match[str]) -> Optional[str]:
    """Return the intended recipient for one valid commentary tool call."""
    channel_header = match.group("channel_header") or ""
    if _channel_name(channel_header) != "commentary":
        return None
    if not _is_call_terminator(match.group("terminator") or ""):
        return None
    return extract_gpt_oss_recipient(
        match.group("role_header"), channel_header
    )


def _channel_name(channel_header: str) -> str:
    """Return the leading channel name from one Harmony header."""
    stripped = (channel_header or "").strip()
    return stripped.split()[0] if stripped else ""


def _is_call_terminator(terminator: str) -> bool:
    """Return whether one Harmony terminator still represents a tool call."""
    return terminator in {"<|call|>", ""}


def _is_functions_recipient(recipient: Optional[str]) -> bool:
    """Return whether one commentary recipient targets our tool namespace."""
    return bool(recipient and recipient.startswith("functions."))


def _load_tool_arguments(
    adapter: Any,
    recipient: str,
    body: str,
) -> Optional[Dict[str, Any]]:
    """Load one commentary tool-call argument body as JSON."""
    try:
        arguments = json.loads(body)
    except json.JSONDecodeError as exc:
        adapter.logger.warning(
            "Failed to parse GPT-OSS Harmony tool call JSON for %s: %s",
            recipient,
            exc,
        )
        return None
    if isinstance(arguments, dict):
        return arguments
    return {}


def extract_gpt_oss_recipient(
    role_header: Optional[str],
    channel_header: str,
) -> Optional[str]:
    """Return the Harmony tool recipient from role or channel header."""
    for header in (role_header or "", channel_header or ""):
        match = re.search(r"\bto=([^\s<]+)", header)
        if match:
            return match.group(1).strip()
    return None
