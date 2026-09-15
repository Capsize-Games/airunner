"""JSON parsing helpers for HuggingFace tool-call extraction."""

from __future__ import annotations

import json
import re
from typing import Any, Optional, Tuple

from airunner_services.llm.adapters.mixins.tool_call_payload_helpers import (
    extract_tool_call,
    is_tool_payload,
    normalize_tool_payload,
)


def try_parse_json_blocks(
    adapter: Any,
    response_text: str,
) -> Optional[Tuple[list[dict], str]]:
    """Try extracting tool-call JSON from fenced code blocks."""
    json_block_pattern = r"```json\s*(\{[^`]+\})\s*```"
    tool_calls = _tool_calls_from_json_blocks(
        adapter,
        response_text,
        json_block_pattern,
    )
    if not tool_calls:
        return None
    cleaned_text = re.sub(
        json_block_pattern,
        "",
        response_text,
        flags=re.DOTALL,
    ).strip()
    return tool_calls, cleaned_text


def _tool_calls_from_json_blocks(
    adapter: Any,
    response_text: str,
    json_block_pattern: str,
) -> list[dict]:
    """Return tool calls parsed from fenced JSON blocks."""
    tool_calls: list[dict] = []
    matches = re.findall(json_block_pattern, response_text, re.DOTALL)
    for match in matches:
        _append_json_tool_call(adapter, tool_calls, match)
    return tool_calls


def _append_json_tool_call(
    adapter: Any,
    tool_calls: list[dict],
    json_text: str,
) -> None:
    """Append one tool call parsed from JSON when valid."""
    try:
        data = normalize_tool_payload(json.loads(json_text))
    except json.JSONDecodeError as error:
        adapter.logger.error("Failed to parse JSON block: %s", error)
        return
    if is_tool_payload(data):
        tool_calls.append(extract_tool_call(data))


def try_parse_embedded_json(
    adapter: Any,
    response_text: str,
) -> Optional[Tuple[list[dict], str]]:
    """Try extracting tool-call JSON objects embedded in text."""
    json_pattern = r'\{(?:[^{}]|(\{(?:[^{}]|\{[^{}]*\})*\}))*\}'
    tool_calls: list[dict] = []
    cleaned_text = response_text
    for match in re.finditer(json_pattern, response_text, re.DOTALL):
        cleaned_text = _append_embedded_tool_call(
            adapter,
            tool_calls,
            cleaned_text,
            match.group(0),
        )
    if not tool_calls:
        return None
    return tool_calls, cleaned_text


def try_parse_tool_call_tags(
    adapter: Any,
    response_text: str,
) -> Optional[Tuple[list[dict], str]]:
    """Try extracting tool calls from `<tool_call>` XML wrappers."""
    tool_call_tag_pattern = r"<tool_call>\s*(\{[^<]+\})\s*</tool_call>"
    matches = re.findall(tool_call_tag_pattern, response_text, re.DOTALL)
    if not matches:
        return None
    tool_calls = _tool_calls_from_tag_matches(adapter, matches)
    return _tool_call_tag_result(
        response_text,
        tool_call_tag_pattern,
        tool_calls,
    )


def _tool_call_tag_result(
    response_text: str,
    tool_call_tag_pattern: str,
    tool_calls: list[dict],
) -> Optional[Tuple[list[dict], str]]:
    """Return parsed tool calls or cleaned fallback text for tag payloads."""
    if tool_calls:
        cleaned_text = re.sub(
            tool_call_tag_pattern,
            "",
            response_text,
            flags=re.DOTALL,
        ).strip()
        return tool_calls, cleaned_text
    cleaned_text = re.sub(
        tool_call_tag_pattern,
        lambda match: match.group(1),
        response_text,
        flags=re.DOTALL,
    ).strip()
    return None, cleaned_text


def _tool_calls_from_tag_matches(
    adapter: Any,
    matches: list[str],
) -> list[dict]:
    """Return tool calls parsed from `<tool_call>` tag payloads."""
    tool_calls: list[dict] = []
    for match in matches:
        _append_tool_call_tag(adapter, tool_calls, match)
    return tool_calls


def _append_tool_call_tag(
    adapter: Any,
    tool_calls: list[dict],
    json_text: str,
) -> None:
    """Append one tool call parsed from a tag-wrapped JSON payload."""
    try:
        data = normalize_tool_payload(json.loads(json_text.strip()))
    except json.JSONDecodeError as error:
        adapter.logger.debug(
            "Failed to parse JSON in <tool_call> tag: %s",
            error,
        )
        return
    if isinstance(data, dict) and is_tool_payload(data):
        tool_calls.append(extract_tool_call(data))


def _append_embedded_tool_call(
    adapter: Any,
    tool_calls: list[dict],
    cleaned_text: str,
    json_text: str,
) -> str:
    """Append one embedded tool call and return updated cleaned text."""
    try:
        data = normalize_tool_payload(json.loads(json_text))
    except json.JSONDecodeError:
        return cleaned_text
    if not is_tool_payload(data):
        return cleaned_text
    tool_call = extract_tool_call(data)
    tool_calls.append(tool_call)
    adapter.logger.debug(
        "Parsed embedded JSON tool call: %s",
        tool_call["name"],
    )
    return cleaned_text.replace(json_text, "").strip()