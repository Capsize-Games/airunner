"""Harmony prompt-completion helpers for the GGUF chat adapter."""

import json
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

from airunner_services.llm.adapters.chat_gguf_prompt_harmony_render import (
    render_gpt_oss_ai_message,
    render_gpt_oss_developer_message,
    render_gpt_oss_prefilled_tool_call,
    render_gpt_oss_tool_message,
    render_harmony_message,
    stringify_harmony_content,
)
from airunner_services.llm.adapters.chat_gguf_prompt_instructions import (
    gpt_oss_harmony_system_message,
)
from airunner_services.llm.gpt_oss_parser import START_TOKEN


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