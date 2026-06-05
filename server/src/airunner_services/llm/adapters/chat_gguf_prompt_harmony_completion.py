"""Harmony prompt-completion helpers for the GGUF chat adapter."""

import json
from typing import Any, Dict, List, Optional

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from airunner_services.llm.adapters.chat_gguf_prompt_harmony_render import (
    render_gpt_oss_ai_message,
    render_gpt_oss_developer_message,
    render_gpt_oss_prefilled_tool_call,
    render_gpt_oss_tool_message,
    render_harmony_message,
    stringify_harmony_content,
)
from airunner_services.llm.adapters.chat_gguf_generation_helper import (
    effective_max_tokens,
)
from airunner_services.llm.adapters.chat_gguf_prompt_instructions import (
    gpt_oss_harmony_system_message,
)
from airunner_services.llm.gpt_oss_parser import START_TOKEN


def _system_prompt_parts(
    adapter: Any,
    messages: List[BaseMessage],
) -> List[str]:
    """Build the leading Harmony system and developer prompt parts."""
    prompt_parts = [
        render_harmony_message(
            "system",
            gpt_oss_harmony_system_message(adapter),
        )
    ]
    developer_message = render_gpt_oss_developer_message(adapter, messages)
    if developer_message:
        prompt_parts.append(developer_message)
    return prompt_parts


def _render_history_message(
    adapter: Any,
    message: BaseMessage,
) -> List[str]:
    """Render one non-system LangChain message into Harmony parts."""
    if isinstance(message, HumanMessage):
        return [
            render_harmony_message(
                "user",
                stringify_harmony_content(message.content),
            )
        ]
    if isinstance(message, AIMessage):
        return render_gpt_oss_ai_message(adapter, message)
    if isinstance(message, ToolMessage):
        return [render_gpt_oss_tool_message(message)]
    return []


def _assistant_prompt_suffix(adapter: Any) -> str:
    """Return the trailing assistant prefix for one Harmony prompt."""
    forced_tool_name = adapter._forced_gpt_oss_tool_name()
    if forced_tool_name:
        return render_gpt_oss_prefilled_tool_call(forced_tool_name)
    return f"{START_TOKEN}assistant"


def render_gpt_oss_harmony_prompt(
    adapter: Any,
    messages: List[BaseMessage],
) -> str:
    """Render LangChain messages as one raw Harmony prompt."""
    prompt_parts = _system_prompt_parts(adapter, messages)
    for message in messages:
        if isinstance(message, SystemMessage):
            continue
        prompt_parts.extend(_render_history_message(adapter, message))
    prompt_parts.append(_assistant_prompt_suffix(adapter))
    return "".join(prompt_parts)


def build_gpt_oss_completion_kwargs(
    adapter: Any,
    messages: List[BaseMessage],
    stop: Optional[List[str]],
    *,
    stream: bool,
) -> Dict[str, Any]:
    """Build llama.cpp completion kwargs for raw Harmony prompting."""
    max_tokens = effective_max_tokens(adapter, adapter.max_tokens)
    completion_kwargs: Dict[str, Any] = {
        "prompt": render_gpt_oss_harmony_prompt(adapter, messages),
        "max_tokens": max_tokens,
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


def _continuation_kwargs(
    adapter: Any,
    completion_kwargs: Dict[str, Any],
    combined: str,
) -> Dict[str, Any]:
    """Build one follow-up completion request for a truncated tool body."""
    continuation_kwargs = dict(completion_kwargs)
    continuation_kwargs["prompt"] = f"{completion_kwargs['prompt']}{combined}"
    continuation_kwargs["max_tokens"] = min(adapter.max_tokens, 512)
    return continuation_kwargs


def _continuation_text(response: Dict[str, Any]) -> str:
    """Extract one continuation text payload from a completion response."""
    choice = response["choices"][0]
    return choice.get("text", "") or ""


def _log_tool_json_continuation(adapter: Any, attempt: int) -> None:
    """Log one continuation attempt for forced Harmony tool JSON."""
    adapter.logger.info(
        "Continuing incomplete prefilled GPT-OSS tool JSON " "(attempt %s)",
        attempt + 1,
    )


def continue_prefilled_gpt_oss_tool_call(
    adapter: Any,
    completion_kwargs: Dict[str, Any],
    raw_text: str,
) -> str:
    """Continue a truncated prefilled Harmony tool call body."""
    combined = raw_text or ""
    for attempt in range(2):
        if not prefilled_gpt_oss_tool_json_needs_continuation(
            adapter, combined
        ):
            break
        response = adapter._llama.create_completion(
            **_continuation_kwargs(adapter, completion_kwargs, combined)
        )
        continuation_text = _continuation_text(response)
        if not continuation_text:
            break
        _log_tool_json_continuation(adapter, attempt)
        combined += continuation_text
    return combined
