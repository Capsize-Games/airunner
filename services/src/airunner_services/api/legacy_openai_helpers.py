"""Shared helpers for legacy OpenAI-compatible endpoints."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

from airunner_services.llm.llm_request import LLMRequest


TOOL_CALL_PATTERN = re.compile(
    r'\{[\s]*"tool_call"[\s]*:[\s]*\{[^}]+\}[\s]*\}',
    re.DOTALL,
)


def extract_prompt_and_system(
    messages: list[dict[str, Any]],
) -> tuple[str, str]:
    """Return the last user prompt and latest system prompt."""
    system_prompt = ""
    last_user_content = ""
    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        if role == "system":
            system_prompt = content
        if role == "user":
            last_user_content = content
    return last_user_content, system_prompt


def enhance_system_prompt(
    system_prompt: str,
    tools: list[dict[str, Any]],
) -> str:
    """Append tool descriptions to the system prompt when provided."""
    if not tools:
        return system_prompt
    sections = [section for section in [system_prompt, format_tools_for_prompt(tools)] if section]
    return "\n\n".join(sections)


def create_llm_request(
    *,
    temperature: Any,
    max_tokens: Any,
    system_prompt: str,
    has_tools: bool,
) -> LLMRequest:
    """Create an LLMRequest for OpenAI-compatible chat requests."""
    llm_request = LLMRequest()
    llm_request.temperature = temperature
    llm_request.max_new_tokens = max_tokens
    if system_prompt:
        llm_request.system_prompt = system_prompt
    llm_request.use_memory = False
    llm_request.tool_categories = None if has_tools else []
    return llm_request


def format_tools_for_prompt(tools: list[dict[str, Any]]) -> str:
    """Render OpenAI-style tool definitions into prompt instructions."""
    if not tools:
        return ""
    lines = ["You have access to the following tools:"]
    for tool in tools:
        lines.extend(_tool_description_lines(tool))
    lines.extend(_tool_usage_suffix())
    return "\n".join(lines)


def parse_tool_calls_from_response(
    response_text: str | None,
    tools: list[dict[str, Any]] | None,
) -> tuple[str | None, list[dict[str, Any]]]:
    """Extract tool calls from model text and strip them from content."""
    if not tools or not response_text:
        return response_text, []
    tool_calls = _parsed_tool_calls(response_text)
    if not tool_calls:
        return response_text, []
    content = TOOL_CALL_PATTERN.sub("", response_text).strip()
    return content or None, tool_calls


def build_usage(prompt: str, completion: str) -> dict[str, int]:
    """Return the OpenAI-style token usage payload."""
    return {
        "prompt_tokens": len(prompt) // 4,
        "completion_tokens": len(completion) // 4,
        "total_tokens": (len(prompt) + len(completion)) // 4,
    }


def _tool_description_lines(tool: dict[str, Any]) -> list[str]:
    """Return formatted prompt lines for one function tool definition."""
    if tool.get("type") != "function":
        return []
    function = tool.get("function", {})
    lines = [f"\n**{function.get('name', '')}**: {function.get('description', '')}"]
    parameters = function.get("parameters", {})
    properties = parameters.get("properties") or {}
    if not properties:
        return lines
    lines.append("  Parameters:")
    for name, info in properties.items():
        lines.append(_parameter_line(name, info, parameters.get("required", [])))
    return lines


def _parameter_line(
    name: str,
    info: dict[str, Any],
    required_names: list[str],
) -> str:
    """Return one formatted parameter line for a tool definition."""
    param_type = info.get("type", "any")
    required = " (required)" if name in required_names else " (optional)"
    description = info.get("description", "")
    return f"    - {name}: {param_type}{required} - {description}"


def _tool_usage_suffix() -> list[str]:
    """Return the fixed tool-usage prompt suffix."""
    return [
        "\nTo use a tool, respond with a JSON object in this format:",
        '{"tool_call": {"name": "tool_name", "arguments": {"arg1": "value1"}}}',
        "\nOnly use a tool if it's necessary to answer the user's question.",
    ]


def _parsed_tool_calls(response_text: str) -> list[dict[str, Any]]:
    """Return parsed tool-call entries found in the model response."""
    tool_calls: list[dict[str, Any]] = []
    for match in TOOL_CALL_PATTERN.findall(response_text):
        entry = _parsed_tool_call_match(match)
        if entry is not None:
            tool_calls.append(entry)
    return tool_calls


def _parsed_tool_call_match(match: str) -> dict[str, Any] | None:
    """Return one parsed tool-call entry from a JSON snippet."""
    try:
        parsed = json.loads(match)
    except json.JSONDecodeError:
        return None
    if "tool_call" not in parsed:
        return None
    tool_call = parsed["tool_call"]
    return {
        "id": f"call_{uuid.uuid4().hex[:8]}",
        "type": "function",
        "function": {
            "name": tool_call.get("name", ""),
            "arguments": json.dumps(tool_call.get("arguments", {})),
        },
    }