"""Conversation-title helpers for generation."""

from __future__ import annotations

from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from airunner_services.contract_enums import SignalCode
from airunner_services.database.models.conversation import Conversation

TITLE_PASS_SYSTEM_PROMPT = (
    "You generate short conversation titles for chat history. "
    "Return only one concise title in 3 to 7 words. "
    "Do not use quotes, markdown, emojis, or trailing punctuation. "
    "If the exchange is just a greeting or opening pleasantry, return "
    "'Greeting and introduction'."
)


def conversation_for_title_pass(owner) -> Optional[Conversation]:
    """Return one untitled conversation ready for the title pass."""
    workflow_manager = getattr(owner, "_workflow_manager", None)
    conversation_id = getattr(workflow_manager, "_conversation_id", None)
    if not conversation_id:
        return None
    try:
        conversation = Conversation.objects.get(conversation_id)
    except Exception:
        owner.logger.warning(
            "Failed to load conversation %s for title pass",
            conversation_id,
        )
        return None
    if (
        not conversation
        or str(getattr(conversation, "title", "") or "").strip()
    ):
        return None
    return conversation


def title_pass_messages(conversation: Conversation) -> list[dict[str, str]]:
    """Return visible user and assistant messages for title generation."""
    messages = []
    for item in list(getattr(conversation, "value", None) or []):
        role = str(item.get("role") or "").strip().lower()
        if role not in {"user", "assistant", "bot"}:
            continue
        if item.get("metadata_type") in {"tool_calls", "tool_result"}:
            continue
        content = str(item.get("content") or "").strip()
        if content:
            messages.append({"role": role, "content": content})
    return messages


def build_title_pass_prompt(messages: list[dict[str, str]]) -> list[Any]:
    """Build one short title-generation prompt from the visible exchange."""
    exchange = "\n".join(
        f"{item['role'].title()}: {item['content'][:500]}"
        for item in messages[:6]
    )
    return [
        SystemMessage(content=TITLE_PASS_SYSTEM_PROMPT),
        HumanMessage(content=f"Conversation:\n{exchange}\n\nTitle:"),
    ]


def sanitize_generated_title(raw_title: Any) -> str:
    """Normalize one model-produced title into a single plain line."""
    title = str(raw_title or "").strip()
    if not title:
        return ""
    title = title.splitlines()[0].strip().strip("\"'` ")
    title = title.rstrip(".!?:;,- ")
    return title[:80].strip()


def maybe_generate_conversation_title(owner) -> None:
    """Persist one LLM-generated title after the first assistant reply."""
    conversation = conversation_for_title_pass(owner)
    if conversation is None or owner._chat_model is None:
        return
    messages = title_pass_messages(conversation)
    roles = {item["role"] for item in messages}
    if "user" not in roles or not ({"assistant", "bot"} & roles):
        return
    try:
        response = owner._chat_model.invoke(build_title_pass_prompt(messages))
        title = sanitize_generated_title(
            getattr(response, "content", response)
        )
        if not title:
            return
        Conversation.objects.update(conversation.id, title=title)
        emit = getattr(owner, "emit_signal", None)
        if callable(emit):
            emit(
                SignalCode.CONVERSATION_TITLE_UPDATED,
                {"conversation_id": conversation.id, "title": title},
            )
    except Exception as exc:
        owner.logger.warning(
            "Failed to generate conversation title for %s: %s",
            getattr(conversation, "id", None),
            exc,
        )
