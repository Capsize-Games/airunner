"""Generation helpers extracted from the ChatGGUF adapter."""

from __future__ import annotations

import time
from typing import Any, Optional

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from airunner_services.llm.adapters.chat_gguf_generation_request import (
    chat_completion_kwargs,
    generate_raw_gpt_oss_result,
)
from airunner_services.llm.adapters.chat_gguf_response_message import (
    response_message,
)
from airunner_services.utils.application.log_hygiene import (
    summarize_mapping_keys,
)

QWEN_NO_THINK_MIN_TOKENS = 48
GPT_OSS_MIN_TOKENS = 64


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
        return generate_raw_gpt_oss_result(
            adapter,
            messages,
            stop,
            effective_max_tokens,
        )
    chat_kwargs = _chat_completion_request_kwargs(adapter, messages, stop)
    _log_tool_mode(adapter)
    response = _call_chat_completion(adapter, chat_kwargs)
    return _chat_result(_response_message(adapter, response))


def _chat_completion_request_kwargs(
    adapter: Any,
    messages: list[BaseMessage],
    stop: Optional[list[str]],
) -> dict[str, Any]:
    """Build llama.cpp chat-completion kwargs for one request."""
    return chat_completion_kwargs(
        adapter,
        adapter._convert_messages(messages),
        stop,
        effective_max_tokens,
    )


def _chat_result(message: AIMessage) -> ChatResult:
    """Wrap one AI message in the ChatResult envelope."""
    return ChatResult(generations=[ChatGeneration(message=message)])


def effective_max_tokens(
    adapter: Any,
    requested_max_tokens: Optional[int],
) -> Optional[int]:
    """Return the effective max token budget for one GGUF request."""
    if requested_max_tokens is None:
        return None
    max_tokens = int(requested_max_tokens)
    if _needs_qwen_no_think_floor(adapter):
        return max(max_tokens, QWEN_NO_THINK_MIN_TOKENS)
    if _needs_gpt_oss_floor(adapter):
        return max(max_tokens, GPT_OSS_MIN_TOKENS)
    return max_tokens


def _needs_qwen_no_think_floor(adapter: Any) -> bool:
    """Return True when Qwen no-think needs a minimum token floor."""
    model_path = str(getattr(adapter, "model_path", "")).lower()
    return (
        not getattr(adapter, "enable_thinking", True) and "qwen3" in model_path
    )


def _needs_gpt_oss_floor(adapter: Any) -> bool:
    """Return True when GPT-OSS Harmony needs room to reach `final`."""
    return adapter._uses_gpt_oss_parser()


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
    return response_message(adapter, response)
