"""GPT-OSS and Harmony tool-parsing helpers for ChatGGUF."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage

from airunner_services.llm.adapters.chat_gguf_tool_parsing_common import (
    _tool_call,
    normalize_tool_payload,
)
from airunner_services.llm.gpt_oss_parser import (
    CALL_TOKEN,
    END_TOKEN,
    RETURN_TOKEN,
    looks_like_tool_argument_payload,
    parse_gpt_oss_response,
)


def forced_gpt_oss_tool_name(adapter: Any) -> Optional[str]:
    """Return the forced tool name for raw Harmony prompting."""
    if not adapter._use_raw_gpt_oss_completion():
        return None
    tool_name = _tool_name_from_choice(adapter.tool_choice)
    if not tool_name:
        return None
    available_tools = {
        (tool.get("function", tool) or {}).get("name")
        for tool in adapter.tools or []
    }
    if available_tools and tool_name not in available_tools:
        adapter.logger.warning(
            "Forced GPT-OSS tool %s missing from bound tools %s; "
            "continuing with explicit tool_choice",
            tool_name,
            sorted(name for name in available_tools if name),
        )
    return tool_name


def _tool_name_from_choice(tool_choice: Any) -> Optional[str]:
    """Return the tool name encoded in one tool_choice payload."""
    if isinstance(tool_choice, str):
        normalized = tool_choice.strip()
        if normalized and normalized not in {"auto", "none"}:
            return normalized
    if isinstance(tool_choice, dict):
        function = tool_choice.get("function") or {}
        return function.get("name")
    return None


def build_gpt_oss_message_from_raw(
    adapter: Any,
    raw_text: str,
) -> AIMessage:
    """Normalize one raw Harmony completion into an AIMessage."""
    parsed = parse_gpt_oss_response(raw_text)
    content = parsed.content
    tool_calls = parse_gpt_oss_commentary_tool_calls(adapter, raw_text)
    suppressed_prefilled_payload = False
    if not tool_calls:
        tool_calls = parse_prefilled_gpt_oss_tool_call(adapter, raw_text)
        if not tool_calls:
            suppressed_prefilled_payload = bool(
                forced_gpt_oss_tool_name(adapter)
            ) and looks_like_tool_argument_payload(raw_text)
    if tool_calls:
        content = ""
    else:
        tool_calls, content = adapter._extract_tool_calls(content or raw_text)
        if suppressed_prefilled_payload and not tool_calls:
            adapter.logger.warning(
                "Suppressing malformed prefilled GPT-OSS tool payload"
            )
            content = ""
    additional_kwargs = _message_additional_kwargs(
        parsed.thinking_content,
        suppressed_prefilled_payload,
    )
    return AIMessage(
        content=content,
        tool_calls=tool_calls,
        additional_kwargs=additional_kwargs,
    )


def _message_additional_kwargs(
    thinking_content: str,
    suppressed_prefilled_payload: bool,
) -> Dict[str, Any]:
    """Return additional kwargs for one parsed AIMessage."""
    additional_kwargs: Dict[str, Any] = {}
    if thinking_content:
        additional_kwargs["thinking_content"] = thinking_content
    if suppressed_prefilled_payload:
        additional_kwargs["suppressed_malformed_tool_payload"] = True
    return additional_kwargs


def parse_gpt_oss_commentary_tool_calls(
    adapter: Any,
    content: str,
) -> List[Dict[str, Any]]:
    """Parse GPT-OSS Harmony commentary tool calls from raw output."""
    tool_calls: List[Dict[str, Any]] = []
    pattern = re.compile(
        r"(?:<\|start\|>assistant(?P<role_header>[^<]*))?"
        r"<\|channel\|>(?P<channel_header>[^<]*)"
        r"(?:<\|constrain\|>(?P<constraint>[^<]*))?"
        r"<\|message\|>(?P<body>.*?)(?P<terminator><\|call\|>|"
        r"<\|end\|>|<\|return\|>|$)",
        re.DOTALL,
    )
    for match in pattern.finditer(content or ""):
        channel_header = (match.group("channel_header") or "").strip()
        channel_name = channel_header.split()[0] if channel_header else ""
        if channel_name != "commentary":
            continue
        terminator = match.group("terminator") or ""
        if terminator not in {"<|call|>", ""}:
            continue
        recipient = extract_gpt_oss_recipient(
            match.group("role_header"),
            channel_header,
        )
        if not recipient or not recipient.startswith("functions."):
            continue
        body = (match.group("body") or "").strip()
        if not body:
            continue
        arguments = _load_tool_arguments(adapter, recipient, body)
        if arguments is None:
            continue
        tool_calls.append(
            {
                "id": str(uuid.uuid4()),
                "name": recipient.removeprefix("functions."),
                "args": arguments,
                "type": "tool_call",
            }
        )
    return tool_calls


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


def extract_prefilled_gpt_oss_tool_json(content: str) -> str:
    """Return JSON emitted after a prefilled Harmony tool envelope."""
    candidate = (content or "").strip()
    if not candidate:
        return ""
    candidate = _trim_prefilled_markers(candidate)
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", candidate, re.DOTALL)
    if fenced:
        candidate = fenced.group(1).strip()
    if not candidate.startswith("{"):
        return ""
    try:
        _, end_index = json.JSONDecoder().raw_decode(candidate)
    except json.JSONDecodeError:
        return candidate
    return candidate[:end_index].strip()


def _trim_prefilled_markers(candidate: str) -> str:
    """Trim Harmony terminators from a prefilled tool payload."""
    marker_indexes = [
        candidate.find(token)
        for token in (CALL_TOKEN, END_TOKEN, RETURN_TOKEN)
        if token in candidate
    ]
    if marker_indexes:
        return candidate[: min(marker_indexes)].strip()
    return candidate


def parse_prefilled_gpt_oss_tool_call(
    adapter: Any,
    content: str,
) -> List[Dict[str, Any]]:
    """Parse one forced Harmony tool call from a bare JSON body."""
    tool_name = forced_gpt_oss_tool_name(adapter)
    json_text = extract_prefilled_gpt_oss_tool_json(content)
    if not tool_name or not json_text:
        return []
    try:
        arguments = normalize_tool_payload(json.loads(json_text))
    except json.JSONDecodeError as exc:
        adapter.logger.warning(
            "Failed to parse prefilled GPT-OSS tool JSON for %s: %s",
            tool_name,
            exc,
        )
        return []
    if not isinstance(arguments, dict):
        return []
    return [_tool_call(tool_name, arguments)]


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