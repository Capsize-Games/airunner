"""Formatting helpers for manual tool prompts."""

from __future__ import annotations


def format_tools_for_prompt(tools: list[dict]) -> str:
    """Format tools as one manual prompt block."""
    if not tools:
        return ""
    tool_strings = build_tool_descriptions(tools)
    return "\n\n".join(tool_strings)


def build_tool_descriptions(tools: list[dict]) -> list[str]:
    """Build formatted descriptions for each tool."""
    tool_strings: list[str] = []
    for tool in tools:
        tool_strings.append(_tool_description(tool))
    return tool_strings


def _tool_description(tool: dict) -> str:
    """Return one formatted tool description."""
    tool_str = (
        f"- {tool['function']['name']}: " f"{tool['function']['description']}"
    )
    params = tool["function"].get("parameters", {}).get("properties", {})
    if not params:
        return tool_str
    return tool_str + "\n" + "\n".join(format_parameters(params))


def format_parameters(params: dict) -> list[str]:
    """Format tool parameters as prompt lines."""
    param_strs: list[str] = []
    for param_name, param_info in params.items():
        param_type = param_info.get("type", "string")
        param_desc = param_info.get("description", "")
        param_strs.append(f"  - {param_name} ({param_type}): {param_desc}")
    return param_strs
