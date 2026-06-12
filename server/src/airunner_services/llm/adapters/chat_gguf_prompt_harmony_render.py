"""Harmony rendering helpers for the GGUF chat adapter."""

import json
from typing import Any, Dict, List, Optional, Sequence

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    SystemMessage,
    ToolMessage,
)

from airunner_services.llm.adapters.chat_gguf_prompt_instructions import (
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


def _developer_message_contents(messages: List[BaseMessage]) -> List[str]:
    """Collect system-message content for the Harmony developer layer."""
    return [
        stringify_harmony_content(message.content)
        for message in messages
        if isinstance(message, SystemMessage)
    ]


def _join_developer_content(contents: List[str]) -> str:
    """Join non-empty developer message content blocks."""
    return "\n\n".join(content for content in contents if content.strip())


def _inject_developer_tool_instructions(
    adapter: Any,
    developer_content: str,
) -> str:
    """Inject tool instructions into the developer layer when needed."""
    if adapter.tools and "namespace functions" not in developer_content:
        return inject_gpt_oss_tool_instructions(adapter, developer_content)
    return developer_content


def render_gpt_oss_developer_message(
    adapter: Any,
    messages: List[BaseMessage],
) -> str:
    """Render the developer instruction layer for raw Harmony prompts."""
    contents = _developer_message_contents(messages)
    if not contents:
        return ""

    developer_content = _join_developer_content(contents)
    developer_content = _inject_developer_tool_instructions(
        adapter,
        developer_content,
    )
    if not developer_content.strip():
        return ""
    return render_harmony_message("developer", developer_content)


def _final_ai_message(message: AIMessage) -> Optional[str]:
    """Render one assistant final channel message when present."""
    content = str(message.content or "").strip()
    if not content:
        return None
    return render_harmony_message(
        "assistant",
        content,
        channel="final",
    )


def render_gpt_oss_ai_message(
    adapter: Any,
    message: AIMessage,
) -> List[str]:
    """Render one historical AI message into Harmony messages.

    Per the Harmony spec, the analysis (chain-of-thought) channel of *past*
    assistant turns must NOT be fed back into the prompt — only the final
    channel (or tool calls) is kept. Re-injecting prior reasoning bloats the
    context every turn, which on gpt-oss's small n_ctx quickly leaves no room
    for generation and truncates the answer.
    """
    rendered: List[str] = []

    tool_calls = getattr(message, "tool_calls", None) or []
    if tool_calls:
        return _render_gpt_oss_tool_calls(tool_calls)

    content = _final_ai_message(message)
    if content:
        rendered.append(content)
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
