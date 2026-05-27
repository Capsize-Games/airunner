"""Message-conversion helpers for the GGUF chat adapter."""

import json
import uuid
from typing import Any, Dict, List, Optional, Sequence

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from airunner_services.llm.adapters.chat_gguf_prompt_instructions import (
    apply_gpt_oss_reasoning_effort,
    apply_thinking_directive,
    inject_tool_instructions,
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