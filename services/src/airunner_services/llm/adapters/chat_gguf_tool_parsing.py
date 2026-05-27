"""Tool-parsing helpers extracted from the ChatGGUF adapter."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage

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


def _tool_call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Build one normalized tool-call payload."""
    return {
        "id": str(uuid.uuid4()),
        "name": tool_name,
        "args": arguments,
        "type": "tool_call",
    }


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