"""Harmony prompt-rendering helpers for the GGUF chat adapter."""

import json
from typing import Any, Dict, List, Optional, Sequence

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from airunner_services.llm.adapters.chat_gguf_prompt_instructions import (
    gpt_oss_harmony_system_message,
    inject_gpt_oss_tool_instructions,
)
from airunner_services.llm.adapters.chat_gguf_prompt_messages import (
    convert_langchain_tool_calls,
)
from airunner_services.llm.gpt_oss_parser import (
    CALL_TOKEN,
    CHANNEL_TOKEN,
    CONSTRAIN_TOKEN,
    END_TOKEN,
    MESSAGE_TOKEN,
    START_TOKEN,
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