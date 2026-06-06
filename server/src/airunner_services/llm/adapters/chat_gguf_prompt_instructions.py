"""Prompt-instruction helpers for the GGUF chat adapter."""

import json
from datetime import date
from typing import Any, Dict, List

from airunner_services.llm.adapters.chat_gguf_prompt_schema import (
    format_gpt_oss_namespace,
)


def apply_gpt_oss_reasoning_effort(
    adapter: Any,
    converted: List[Dict[str, Any]],
) -> None:
    """Inject the documented GPT-OSS reasoning-effort directive."""
    if not adapter._uses_gpt_oss_parser():
        return

    directive = f"reasoning effort {adapter._normalized_reasoning_effort()}"
    for message in converted:
        if _system_message_has_reasoning_directive(message):
            return
        if message.get("role") != "system":
            continue
        _append_reasoning_directive(message, directive)
        return

    converted.insert(0, {"role": "system", "content": directive})


def _system_message_has_reasoning_directive(message: Dict[str, Any]) -> bool:
    """Return whether a system message already sets reasoning effort."""
    if message.get("role") != "system":
        return False
    content = message.get("content")
    if not isinstance(content, str):
        return True
    lowered = content.lower()
    return any(
        directive in lowered
        for directive in (
            "reasoning effort low",
            "reasoning effort medium",
            "reasoning effort high",
        )
    )


def _append_reasoning_directive(
    message: Dict[str, Any],
    directive: str,
) -> None:
    """Append one reasoning directive to a system message."""
    content = message.get("content")
    if not isinstance(content, str):
        return
    message["content"] = (
        f"{content.rstrip()}\n\n{directive}" if content.strip() else directive
    )


def inject_tool_instructions(adapter: Any, system_content: str) -> str:
    """Inject tool instructions into the system prompt."""
    if not adapter.tools or adapter.tool_choice == "none":
        return system_content
    if adapter._uses_gpt_oss_parser():
        return inject_gpt_oss_tool_instructions(adapter, system_content)
    if adapter.tool_calling_mode == "react":
        return inject_react_tool_instructions(adapter, system_content)
    return _inject_xml_tool_instructions(adapter, system_content)


def _inject_xml_tool_instructions(adapter: Any, system_content: str) -> str:
    """Inject Qwen-style XML tool instructions."""
    tool_defs = [json.dumps(tool) for tool in adapter.tools]
    tools_json = "\n".join(tool_defs)
    tool_instructions = f"""

# Tools

You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools> XML tags:
<tools>
{tools_json}
</tools>

For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:
<tool_call>
{{"name": "<function-name>", "arguments": <args-json-object>}}
</tool_call>"""
    return system_content + tool_instructions


def inject_gpt_oss_tool_instructions(
    adapter: Any,
    system_content: str,
) -> str:
    """Inject Harmony-style tool instructions for GPT-OSS."""
    tools_text = format_gpt_oss_namespace(adapter)
    return system_content + _gpt_oss_tool_instructions_text(tools_text)


def _gpt_oss_tool_instructions_text(tools_text: str) -> str:
    """Build the GPT-OSS tool-instruction block."""
    return (
        "\n\n# Valid channels: analysis, commentary, final. "
        "Channel must be included for every message.\n"
        "For coding and editor tasks, avoid analysis-only replies. "
        "Use commentary for brief progress updates and tool calls, "
        "and use final for the finished user-facing answer.\n"
        "Calls to these tools must go to the commentary channel: "
        "'functions'.\n\n"
        "# Tools\n\n"
        "## functions\n\n"
        f"{tools_text}\n\n"
        "When a tool is needed, call it on the commentary channel "
        "with JSON arguments. After tool results arrive, continue "
        "and answer the user on the final channel."
    )


def gpt_oss_harmony_system_message(adapter: Any) -> str:
    """Return the top-level Harmony system message."""
    return (
        "You are ChatGPT, a large language model trained by OpenAI.\n"
        "Knowledge cutoff: 2024-06\n"
        f"Current date: {date.today().isoformat()}\n\n"
        f"Reasoning: {adapter._normalized_reasoning_effort()}\n\n"
        "# Valid channels: analysis, commentary, final. Channel "
        "must be included for every message.\n"
        "Calls to these tools must go to the commentary channel: "
        "'functions'."
    )


def inject_react_tool_instructions(adapter: Any, system_content: str) -> str:
    """Inject ReAct-style tool instructions for text tool calling."""
    tool_defs = []
    for tool in adapter.tools or []:
        func = tool.get("function", tool)
        tool_defs.append(format_react_tool(func))

    tools_text = "\n".join(tool_defs)
    react_instructions = (
        "\n\n# Tools\n\n"
        "You have access to the following tools:\n"
        f"{tools_text}\n\n"
        "To use a tool, respond EXACTLY in this format:\n"
        "Action: tool_name\n"
        'Action Input: {"arg": "value"}\n\n'
        "Do not wrap tool calls in markdown fences. After the tool "
        "result arrives, continue with your answer or the next tool "
        "call."
    )
    return system_content + react_instructions


def format_react_tool(tool: Dict[str, Any]) -> str:
    """Format one OpenAI tool schema as a compact ReAct tool line."""
    name = tool.get("name", "unknown_tool")
    description = tool.get("description", "")
    parameters = tool.get("parameters", {}).get("properties", {})
    required = set(tool.get("parameters", {}).get("required", []))

    args = []
    for param_name, param_info in parameters.items():
        arg_type = param_info.get("type", "any")
        marker = "*" if param_name in required else ""
        args.append(f"{param_name}{marker}: {arg_type}")

    signature = ", ".join(args)
    short_description = description.split(".")[0] if description else ""
    return f"- {name}({signature}) - {short_description}"


def apply_thinking_directive(
    adapter: Any,
    converted: List[Dict[str, Any]],
) -> None:
    """Prefix the final Qwen3 user turn with a no-think directive."""
    model_path = str(adapter.model_path).lower()
    if adapter.enable_thinking or "qwen3" not in model_path:
        return

    for message in reversed(converted):
        if message.get("role") != "user":
            continue
        content = message.get("content")
        if not isinstance(content, str):
            return
        stripped = content.lstrip()
        if stripped.startswith("/no_think") or stripped.startswith("/think"):
            return
        message["content"] = f"/no_think\n{content}"
        return
