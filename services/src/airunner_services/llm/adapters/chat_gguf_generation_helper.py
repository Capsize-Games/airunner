"""Generation helpers extracted from the ChatGGUF adapter."""

from __future__ import annotations

import time
from typing import Any, Optional

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from airunner_services.llm.gpt_oss_parser import (
    has_gpt_oss_markup,
    parse_gpt_oss_response,
)
from airunner_services.utils.application.log_hygiene import (
    summarize_mapping_keys,
)


def generate_chat_result(
    adapter: Any,
    messages: list[BaseMessage],
    stop: Optional[list[str]] = None,
    run_manager: Optional[CallbackManagerForLLMRun] = None,
    **kwargs: Any,
) -> ChatResult:
    """Generate one chat result through llama.cpp."""
    del run_manager, kwargs
    if adapter._use_raw_gpt_oss_completion():
        return _generate_raw_gpt_oss_result(adapter, messages, stop)

    converted_messages = adapter._convert_messages(messages)
    chat_kwargs = _chat_completion_kwargs(adapter, converted_messages, stop)
    _log_tool_mode(adapter)
    response = _call_chat_completion(adapter, chat_kwargs)
    message = _response_message(adapter, response)
    return ChatResult(generations=[ChatGeneration(message=message)])


def _generate_raw_gpt_oss_result(
    adapter: Any,
    messages: list[BaseMessage],
    stop: Optional[list[str]],
) -> ChatResult:
    """Generate one raw Harmony completion result."""
    completion_kwargs = adapter._build_gpt_oss_completion_kwargs(
        messages,
        stop,
        stream=False,
    )
    call_started = time.perf_counter()
    response = adapter._llama.create_completion(**completion_kwargs)
    adapter.logger.info(
        "[ChatGGUF._generate] create_completion returned in %.3fs",
        time.perf_counter() - call_started,
    )
    raw_text = response["choices"][0].get("text", "") or ""
    raw_text = adapter._continue_prefilled_gpt_oss_tool_call(
        completion_kwargs,
        raw_text,
    )
    message = adapter._build_gpt_oss_message_from_raw(raw_text)
    return ChatResult(generations=[ChatGeneration(message=message)])


def _chat_completion_kwargs(
    adapter: Any,
    converted_messages: list[dict[str, Any]],
    stop: Optional[list[str]],
) -> dict[str, Any]:
    """Build one llama.cpp chat completion kwargs payload."""
    chat_kwargs = {
        "messages": converted_messages,
        "max_tokens": adapter.max_tokens,
        "temperature": adapter.temperature,
        "top_p": adapter.top_p,
        "top_k": adapter.top_k,
        "min_p": adapter.min_p,
        "repeat_penalty": adapter.repeat_penalty,
        "stream": False,
    }
    if stop:
        chat_kwargs["stop"] = stop
    if adapter._use_native_tool_calling():
        chat_kwargs["tools"] = adapter.tools
        if adapter.tool_choice is not None:
            chat_kwargs["tool_choice"] = adapter.tool_choice
    return chat_kwargs


def _log_tool_mode(adapter: Any) -> None:
    """Log the current tool-calling mode for one request."""
    if adapter._use_native_tool_calling():
        adapter.logger.debug(
            "[TOOL CALL] Passing %s native tools to llama.cpp",
            len(adapter.tools or []),
        )
    elif adapter.tools:
        adapter.logger.debug(
            "[TOOL CALL] %s tools injected in system prompt",
            len(adapter.tools),
        )
    else:
        adapter.logger.debug("[TOOL CALL] No tools bound")


def _call_chat_completion(
    adapter: Any,
    chat_kwargs: dict[str, Any],
) -> dict[str, Any]:
    """Call llama.cpp chat completion and log the response timing."""
    call_started = time.perf_counter()
    adapter.logger.debug(
        "[TOOL CALL] Calling create_chat_completion with chat_format=%s",
        adapter._detected_format,
    )
    response = adapter._llama.create_chat_completion(**chat_kwargs)
    adapter.logger.info(
        "[ChatGGUF._generate] create_chat_completion returned in %.3fs",
        time.perf_counter() - call_started,
    )
    adapter.logger.debug(
        "[TOOL CALL] Response received (%s)",
        summarize_mapping_keys(response, label="response"),
    )
    return response


def _response_message(adapter: Any, response: dict[str, Any]) -> AIMessage:
    """Build one AIMessage from a llama.cpp response payload."""
    message_data = response["choices"][0].get("message", {})
    content = message_data.get("content", "") or ""
    thinking_content = _thinking_content(adapter, message_data)
    gpt_oss_tool_calls: list[dict[str, Any]] = []
    if adapter._uses_gpt_oss_parser() or has_gpt_oss_markup(content):
        gpt_oss_tool_calls, content, thinking_content = _parse_gpt_oss_content(
            adapter,
            content,
            thinking_content,
        )
    tool_calls, content = _tool_calls_from_message(
        adapter,
        message_data,
        content,
        gpt_oss_tool_calls,
    )
    if tool_calls:
        adapter.logger.debug(
            "[TOOL CALL] Parsed %s tool calls from response",
            len(tool_calls),
        )
    additional_kwargs = {}
    if thinking_content:
        additional_kwargs["thinking_content"] = thinking_content
    return AIMessage(
        content=content,
        tool_calls=tool_calls,
        additional_kwargs=additional_kwargs,
    )


def _thinking_content(adapter: Any, message_data: Any) -> Optional[str]:
    """Return reasoning content from one model message when enabled."""
    if adapter.enable_thinking and hasattr(message_data, "get"):
        return message_data.get("reasoning_content")
    return None


def _parse_gpt_oss_content(
    adapter: Any,
    content: str,
    thinking_content: Optional[str],
) -> tuple[list[dict[str, Any]], str, Optional[str]]:
    """Normalize one GPT-OSS content payload."""
    tool_calls = adapter._parse_gpt_oss_commentary_tool_calls(content)
    parsed = parse_gpt_oss_response(content)
    if not thinking_content:
        thinking_content = parsed.thinking_content
    return tool_calls, parsed.content, thinking_content


def _tool_calls_from_message(
    adapter: Any,
    message_data: Any,
    content: str,
    gpt_oss_tool_calls: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], str]:
    """Return tool calls and cleaned content from one message payload."""
    raw_tool_calls = message_data.get("tool_calls") if hasattr(message_data, "get") else None
    tool_calls = adapter._parse_native_tool_calls(raw_tool_calls)
    if not tool_calls:
        tool_calls, content = adapter._extract_tool_calls(content)
    if not tool_calls and gpt_oss_tool_calls:
        tool_calls = gpt_oss_tool_calls
    return tool_calls, content