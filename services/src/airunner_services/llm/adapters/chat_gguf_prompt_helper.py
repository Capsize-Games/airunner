"""Prompt and message helpers for the GGUF chat adapter."""

import json
import uuid
from datetime import date
from typing import Any, Dict, List, Optional, Sequence

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from airunner_services.llm.gpt_oss_parser import (
    CALL_TOKEN,
    CHANNEL_TOKEN,
    CONSTRAIN_TOKEN,
    END_TOKEN,
    MESSAGE_TOKEN,
    START_TOKEN,
)


def convert_messages(
    adapter: Any,
    messages: List[BaseMessage],
) -> List[Dict[str, Any]]:
    """Convert LangChain messages to llama-cpp message payloads."""
    converted: List[Dict[str, Any]] = []
    tool_instructions_added = False
    use_native_tool_calling = adapter._use_native_tool_calling()

    for message in messages:
        tool_instructions_added = _append_converted_message(
            adapter,
            converted,
            message,
            use_native_tool_calling,
            tool_instructions_added,
        )

    if _needs_tool_system_message(
        adapter,
        use_native_tool_calling,
        tool_instructions_added,
    ):
        converted.insert(
            0,
            {
                "role": "system",
                "content": inject_tool_instructions(adapter, ""),
            },
        )

    apply_gpt_oss_reasoning_effort(adapter, converted)
    apply_thinking_directive(adapter, converted)
    return converted


def _append_converted_message(
    adapter: Any,
    converted: List[Dict[str, Any]],
    message: BaseMessage,
    use_native_tool_calling: bool,
    tool_instructions_added: bool,
) -> bool:
    """Append one converted message and return tool-instruction state."""
    if isinstance(message, SystemMessage):
        return _append_system_message(
            adapter,
            converted,
            message,
            use_native_tool_calling,
            tool_instructions_added,
        )
    if isinstance(message, HumanMessage):
        converted.append({"role": "user", "content": message.content})
        return tool_instructions_added
    if isinstance(message, AIMessage):
        converted.append(_convert_ai_message(adapter, message))
        return tool_instructions_added
    if isinstance(message, ToolMessage):
        converted.append(
            _convert_tool_message(adapter, message, use_native_tool_calling)
        )
    return tool_instructions_added


def _append_system_message(
    adapter: Any,
    converted: List[Dict[str, Any]],
    message: SystemMessage,
    use_native_tool_calling: bool,
    tool_instructions_added: bool,
) -> bool:
    """Append one system message with optional tool instructions."""
    content = message.content
    if _should_inject_tool_instructions(
        adapter,
        use_native_tool_calling,
        tool_instructions_added,
    ):
        content = inject_tool_instructions(adapter, content)
        tool_instructions_added = True
    converted.append({"role": "system", "content": content})
    return tool_instructions_added


def _convert_ai_message(adapter: Any, message: AIMessage) -> Dict[str, Any]:
    """Convert one assistant message to llama-cpp format."""
    message_dict: Dict[str, Any] = {"role": "assistant"}
    tool_calls = convert_langchain_tool_calls(
        getattr(message, "tool_calls", []) or []
    )
    content = message.content or ""
    if adapter._uses_gpt_oss_parser() and tool_calls and not content:
        content = str(message.additional_kwargs.get("thinking_content") or "")
    message_dict["content"] = content
    if tool_calls:
        message_dict["tool_calls"] = tool_calls
    return message_dict


def _convert_tool_message(
    adapter: Any,
    message: ToolMessage,
    use_native_tool_calling: bool,
) -> Dict[str, Any]:
    """Convert one tool result message to llama-cpp format."""
    if adapter._uses_gpt_oss_parser() or use_native_tool_calling:
        return {
            "role": "tool",
            "content": str(message.content),
            "tool_call_id": message.tool_call_id,
        }
    return {
        "role": "user",
        "content": (
            "Tool result for "
            f"{getattr(message, 'name', 'tool')}:\n"
            f"{message.content}"
        ),
    }


def _needs_tool_system_message(
    adapter: Any,
    use_native_tool_calling: bool,
    tool_instructions_added: bool,
) -> bool:
    """Return whether a synthetic tool-aware system message is needed."""
    return bool(
        adapter.tools
        and not use_native_tool_calling
        and not tool_instructions_added
    )


def _should_inject_tool_instructions(
    adapter: Any,
    use_native_tool_calling: bool,
    tool_instructions_added: bool,
) -> bool:
    """Return whether legacy tool instructions should be injected."""
    return bool(
        adapter.tools
        and not use_native_tool_calling
        and not tool_instructions_added
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
        f"{content.rstrip()}\n\n{directive}"
        if content.strip()
        else directive
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
    instructions = (
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
    return system_content + instructions


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


def render_harmony_message(
    role: str,
    content: str,
    *,
    channel: Optional[str] = None,
    recipient: Optional[str] = None,
    content_type: Optional[str] = None,
    terminator: str = END_TOKEN,
) -> str:
    """Render one Harmony protocol message."""
    rendered = [f"{START_TOKEN}{role}"]
    if recipient:
        rendered.append(f" to={recipient}")
    if channel:
        rendered.append(f"{CHANNEL_TOKEN}{channel}")
    if content_type:
        rendered.append(f"{CONSTRAIN_TOKEN}{content_type}")
    rendered.append(f"{MESSAGE_TOKEN}{content}{terminator}")
    return "".join(rendered)


def stringify_harmony_content(content: Any) -> str:
    """Convert one LangChain content payload into Harmony text."""
    if isinstance(content, str):
        return content
    try:
        return json.dumps(content, ensure_ascii=False)
    except TypeError:
        return str(content)


def render_gpt_oss_developer_message(
    adapter: Any,
    messages: List[BaseMessage],
) -> str:
    """Render the developer instruction layer for raw Harmony prompts."""
    contents = [
        stringify_harmony_content(message.content)
        for message in messages
        if isinstance(message, SystemMessage)
    ]
    if not contents:
        return ""

    developer_content = "\n\n".join(
        content for content in contents if content.strip()
    )
    if adapter.tools and "namespace functions" not in developer_content:
        developer_content = inject_gpt_oss_tool_instructions(
            adapter,
            developer_content,
        )
    if not developer_content.strip():
        return ""
    return render_harmony_message("developer", developer_content)


def render_gpt_oss_ai_message(
    adapter: Any,
    message: AIMessage,
) -> List[str]:
    """Render one historical AI message into Harmony messages."""
    rendered: List[str] = []
    thinking = str(
        message.additional_kwargs.get("thinking_content") or ""
    ).strip()
    if thinking:
        rendered.append(
            render_harmony_message(
                "assistant",
                thinking,
                channel="analysis",
            )
        )

    tool_calls = getattr(message, "tool_calls", None) or []
    if tool_calls:
        return _render_gpt_oss_tool_calls(tool_calls)

    content = str(message.content or "").strip()
    if content:
        rendered.append(
            render_harmony_message(
                "assistant",
                content,
                channel="final",
            )
        )
    return rendered


def _render_gpt_oss_tool_calls(
    tool_calls: Sequence[Dict[str, Any]],
) -> List[str]:
    """Render OpenAI-style tool calls into Harmony commentary messages."""
    rendered: List[str] = []
    for tool_call in convert_langchain_tool_calls(tool_calls):
        rendered.append(
            render_harmony_message(
                "assistant",
                tool_call["function"]["arguments"],
                channel="commentary",
                recipient=f"functions.{tool_call['function']['name']}",
                content_type="json",
                terminator=CALL_TOKEN,
            )
        )
    return rendered


def render_gpt_oss_tool_message(message: ToolMessage) -> str:
    """Render one tool-result message into Harmony format."""
    content = str(message.content or "")
    content_type = None
    stripped = content.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        content_type = "json"

    recipient = None
    tool_name = getattr(message, "name", None)
    if tool_name:
        recipient = f"functions.{tool_name}"

    return render_harmony_message(
        "tool",
        content,
        recipient=recipient,
        content_type=content_type,
    )


def render_gpt_oss_prefilled_tool_call(tool_name: str) -> str:
    """Render a partial Harmony tool call for one forced tool."""
    return render_harmony_message(
        "assistant",
        "",
        channel="commentary",
        recipient=f"functions.{tool_name}",
        content_type="json",
        terminator="",
    )


def render_gpt_oss_harmony_prompt(
    adapter: Any,
    messages: List[BaseMessage],
) -> str:
    """Render LangChain messages as one raw Harmony prompt."""
    prompt_parts = [
        render_harmony_message(
            "system",
            gpt_oss_harmony_system_message(adapter),
        )
    ]
    developer_message = render_gpt_oss_developer_message(adapter, messages)
    if developer_message:
        prompt_parts.append(developer_message)

    for message in messages:
        if isinstance(message, SystemMessage):
            continue
        if isinstance(message, HumanMessage):
            prompt_parts.append(
                render_harmony_message(
                    "user",
                    stringify_harmony_content(message.content),
                )
            )
            continue
        if isinstance(message, AIMessage):
            prompt_parts.extend(render_gpt_oss_ai_message(adapter, message))
            continue
        if isinstance(message, ToolMessage):
            prompt_parts.append(render_gpt_oss_tool_message(message))

    forced_tool_name = adapter._forced_gpt_oss_tool_name()
    if forced_tool_name:
        prompt_parts.append(render_gpt_oss_prefilled_tool_call(forced_tool_name))
    else:
        prompt_parts.append(f"{START_TOKEN}assistant")
    return "".join(prompt_parts)


def build_gpt_oss_completion_kwargs(
    adapter: Any,
    messages: List[BaseMessage],
    stop: Optional[List[str]],
    *,
    stream: bool,
) -> Dict[str, Any]:
    """Build llama.cpp completion kwargs for raw Harmony prompting."""
    completion_kwargs: Dict[str, Any] = {
        "prompt": render_gpt_oss_harmony_prompt(adapter, messages),
        "max_tokens": adapter.max_tokens,
        "temperature": adapter.temperature,
        "top_p": adapter.top_p,
        "top_k": adapter.top_k,
        "repeat_penalty": adapter.repeat_penalty,
        "stream": stream,
    }
    if stop:
        completion_kwargs["stop"] = stop
    return completion_kwargs


def prefilled_gpt_oss_tool_json_needs_continuation(
    adapter: Any,
    raw_text: str,
) -> bool:
    """Return True when a forced prefilled tool body looks truncated."""
    if not adapter._forced_gpt_oss_tool_name():
        return False

    json_text = adapter._extract_prefilled_gpt_oss_tool_json(raw_text)
    if not json_text:
        return False

    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError as exc:
        error_text = str(exc).lower()
        if "unterminated string" in error_text:
            return True
        return exc.pos >= max(0, len(json_text) - 16)

    return not isinstance(parsed, dict)


def continue_prefilled_gpt_oss_tool_call(
    adapter: Any,
    completion_kwargs: Dict[str, Any],
    raw_text: str,
) -> str:
    """Continue a truncated prefilled Harmony tool call body."""
    combined = raw_text or ""
    for attempt in range(2):
        if not prefilled_gpt_oss_tool_json_needs_continuation(
            adapter,
            combined,
        ):
            break

        continuation_kwargs = dict(completion_kwargs)
        continuation_kwargs["prompt"] = f"{completion_kwargs['prompt']}{combined}"
        continuation_kwargs["max_tokens"] = min(adapter.max_tokens, 512)

        response = adapter._llama.create_completion(**continuation_kwargs)
        choice = response["choices"][0]
        continuation_text = choice.get("text", "") or ""
        if not continuation_text:
            break

        adapter.logger.info(
            "Continuing incomplete prefilled GPT-OSS tool JSON "
            "(attempt %s)",
            attempt + 1,
        )
        combined += continuation_text

    return combined


def format_gpt_oss_namespace(adapter: Any) -> str:
    """Format bound tools as a Harmony functions namespace."""
    shared_defs: Dict[str, Dict[str, Any]] = {}
    lines = ["namespace functions {", ""]

    for tool in adapter.tools or []:
        function = tool.get("function", tool)
        parameters = function.get("parameters", {})
        shared_defs.update(parameters.get("$defs", {}))

    if shared_defs:
        lines.extend(format_gpt_oss_shared_definitions(shared_defs))
        lines.append("")

    for tool in adapter.tools or []:
        function = tool.get("function", tool)
        lines.extend(format_gpt_oss_tool(function))
        lines.append("")

    while lines and not lines[-1]:
        lines.pop()
    lines.append("} // namespace functions")
    return "\n".join(lines)


def format_gpt_oss_shared_definitions(
    shared_defs: Dict[str, Dict[str, Any]],
) -> List[str]:
    """Format shared schema definitions for Harmony tool prompts."""
    lines: List[str] = []
    for name, schema in shared_defs.items():
        type_definition = format_gpt_oss_type(schema, 1)
        lines.append(f"type {name} = {type_definition};")
    return lines


def format_gpt_oss_tool(tool: Dict[str, Any]) -> List[str]:
    """Format one tool schema as a Harmony type definition."""
    description = tool.get("description", "")
    parameters = tool.get("parameters", {})
    properties = parameters.get("properties", {})
    required = set(parameters.get("required", []))
    name = tool.get("name", "unknown_tool")
    lines = [f"// {description}" if description else "// Tool"]

    if not properties:
        lines.append(f"type {name} = () => any;")
        return lines

    lines.append(f"type {name} = (_: {{")
    for param_name, schema in properties.items():
        param_description = schema.get("description", "")
        if param_description:
            lines.append(f"// {param_description}")
        param_type = format_gpt_oss_type(schema, 1)
        optional = "" if param_name in required else "?"
        lines.append(f"{param_name}{optional}: {param_type},")
    lines.append("}) => any;")
    return lines


def format_gpt_oss_type(
    schema: Dict[str, Any],
    indent_level: int = 0,
) -> str:
    """Convert a JSON schema fragment to a Harmony-style type."""
    if not isinstance(schema, dict):
        return "any"
    if "$ref" in schema:
        return str(schema["$ref"]).rsplit("/", 1)[-1]

    variants = schema.get("anyOf") or schema.get("oneOf")
    if variants:
        return " | ".join(
            format_gpt_oss_type(variant, indent_level)
            for variant in variants
        )
    if "enum" in schema:
        return " | ".join(
            json.dumps(value) for value in schema.get("enum", [])
        )

    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        return " | ".join(str(item) for item in schema_type)
    if schema_type == "array":
        item_type = format_gpt_oss_type(
            schema.get("items", {}),
            indent_level + 1,
        )
        return f"Array<{item_type}>"
    if schema_type == "object":
        return format_gpt_oss_object_type(schema, indent_level + 1)
    if isinstance(schema_type, str):
        return schema_type
    return "any"


def format_gpt_oss_object_type(
    schema: Dict[str, Any],
    indent_level: int,
) -> str:
    """Format one JSON object schema as an inline type block."""
    properties = schema.get("properties", {})
    if not properties:
        return "object"

    required = set(schema.get("required", []))
    indent = "  " * indent_level
    closing_indent = "  " * max(indent_level - 1, 0)
    lines = ["{"]
    for name, child in properties.items():
        child_type = format_gpt_oss_type(child, indent_level + 1)
        optional = "" if name in required else "?"
        lines.append(f"{indent}{name}{optional}: {child_type},")
    lines.append(f"{closing_indent}}}")
    return "\n".join(lines)


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

    function = tool_call.get("function") or {}
    name = tool_call.get("name") or function.get("name")
    if not name:
        return None

    arguments = tool_call.get("args", function.get("arguments", {}))
    if not isinstance(arguments, str):
        try:
            arguments = json.dumps(arguments or {}, sort_keys=True)
        except TypeError:
            arguments = "{}"

    return {
        "id": tool_call.get("id") or str(uuid.uuid4()),
        "type": "function",
        "function": {
            "name": name,
            "arguments": arguments,
        },
    }


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