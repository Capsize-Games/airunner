"""Message-conversion helpers for the GGUF chat adapter."""

from typing import Any, Dict, List, Optional

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
from airunner_services.llm.adapters.chat_gguf_tool_call_conversion import (
    convert_langchain_tool_calls,
)


def _convert_message_history(
    adapter: Any,
    messages: List[BaseMessage],
    use_native_tool_calling: bool,
) -> tuple[List[Dict[str, Any]], bool]:
    """Convert one full history and track whether tool help was injected."""
    converted: List[Dict[str, Any]] = []
    tool_instructions_added = False
    for message in messages:
        tool_instructions_added = _append_converted_message(
            adapter,
            converted,
            message,
            use_native_tool_calling,
            tool_instructions_added,
        )
    return converted, tool_instructions_added


def convert_messages(
    adapter: Any,
    messages: List[BaseMessage],
) -> List[Dict[str, Any]]:
    """Convert LangChain messages to llama-cpp message payloads."""
    use_native_tool_calling = adapter._use_native_tool_calling()
    converted, tool_instructions_added = _convert_message_history(
        adapter,
        messages,
        use_native_tool_calling,
    )
    _prepend_tool_system_message(
        adapter,
        converted,
        use_native_tool_calling,
        tool_instructions_added,
    )
    _finalize_converted_messages(adapter, converted)
    return converted


def _prepend_tool_system_message(
    adapter: Any,
    converted: List[Dict[str, Any]],
    use_native_tool_calling: bool,
    tool_instructions_added: bool,
) -> None:
    """Insert a synthetic system message when tool guidance is still needed."""
    if not _needs_tool_system_message(
        adapter,
        use_native_tool_calling,
        tool_instructions_added,
    ):
        return
    converted.insert(
        0,
        {
            "role": "system",
            "content": inject_tool_instructions(adapter, ""),
        },
    )


def _finalize_converted_messages(
    adapter: Any,
    converted: List[Dict[str, Any]],
) -> None:
    """Apply post-processing directives to converted messages."""
    apply_gpt_oss_reasoning_effort(adapter, converted)
    apply_thinking_directive(adapter, converted)


def _convert_non_system_message(
    adapter: Any,
    message: BaseMessage,
    use_native_tool_calling: bool,
) -> Optional[Dict[str, Any]]:
    """Convert one non-system LangChain message when supported."""
    if isinstance(message, HumanMessage):
        return {"role": "user", "content": message.content}
    if isinstance(message, AIMessage):
        return _convert_ai_message(adapter, message)
    if isinstance(message, ToolMessage):
        return _convert_tool_message(adapter, message, use_native_tool_calling)
    return None


def _append_converted_message(
    adapter: Any,
    converted: List[Dict[str, Any]],
    message: BaseMessage,
    use_native_tool_calling: bool,
    tool_instructions_added: bool,
) -> bool:
    """Append one converted message and return tool-instruction state."""
    if not isinstance(message, SystemMessage):
        _append_non_system_message(
            adapter, converted, message, use_native_tool_calling
        )
        return tool_instructions_added
    return _append_system_message(
        adapter,
        converted,
        message,
        use_native_tool_calling,
        tool_instructions_added,
    )


def _append_non_system_message(
    adapter: Any,
    converted: List[Dict[str, Any]],
    message: BaseMessage,
    use_native_tool_calling: bool,
) -> None:
    """Append one converted non-system message when supported."""
    converted_message = _convert_non_system_message(
        adapter,
        message,
        use_native_tool_calling,
    )
    if converted_message is not None:
        converted.append(converted_message)


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