"""In-context conversation summarization triggered after each generation turn."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    pass


def maybe_summarize_checkpoint(owner: Any) -> None:
    """Summarize old messages in the checkpoint when the threshold is exceeded.

    Reads `perform_conversation_summary` and `summarize_after_n_turns` from
    `owner.llm_settings`.  When enabled and the current thread has more
    human/AI message pairs than the threshold, the oldest messages are
    compressed into a single SystemMessage summary and the checkpoint is
    updated in-memory so the next invocation sees the shorter history.

    Args:
        owner: The LLMModelManager instance (has `_workflow_manager`,
               `llm_settings`, and `logger` attributes).
    """
    try:
        settings = getattr(owner, "llm_settings", None)
        if not settings:
            return
        if not getattr(settings, "perform_conversation_summary", False):
            return
        threshold = getattr(settings, "summarize_after_n_turns", 0)
        if not threshold or threshold <= 0:
            return

        wm = getattr(owner, "_workflow_manager", None)
        if wm is None:
            return

        memory = getattr(wm, "_memory", None)
        thread_id = getattr(wm, "_thread_id", None)
        if memory is None or thread_id is None:
            return

        checkpoint_state = getattr(memory, "_checkpoint_state", {})
        state = checkpoint_state.get(thread_id)
        if not state:
            return

        messages = state.get("messages", [])
        if len(messages) <= threshold:
            return

        owner.logger.info(
            "[SUMMARIZE] %d messages > threshold %d — compressing",
            len(messages),
            threshold,
        )
        summary = _call_llm_for_summary(wm, messages[:-threshold])
        if not summary:
            owner.logger.warning("[SUMMARIZE] LLM returned empty summary, skipping")
            return

        from langchain_core.messages import SystemMessage

        summary_msg = SystemMessage(
            content=f"[Conversation summary — older messages compressed]\n{summary}"
        )
        new_messages = [summary_msg] + list(messages[-threshold:])

        # Update in-memory state so the next invocation uses the compressed list.
        # Also update the checkpoint data structure so get_tuple returns it.
        state["messages"] = new_messages
        checkpoint_data = state.get("checkpoint", {})
        channel_values = checkpoint_data.get("channel_values", {})
        channel_values["messages"] = new_messages
        checkpoint_data["channel_values"] = channel_values
        state["checkpoint"] = checkpoint_data
        checkpoint_state[thread_id] = state

        owner.logger.info(
            "[SUMMARIZE] Compressed %d → %d messages",
            len(messages),
            len(new_messages),
        )
    except Exception as exc:
        try:
            owner.logger.warning("[SUMMARIZE] Error during summarization: %s", exc)
        except Exception:
            pass


def _call_llm_for_summary(wm: Any, messages_to_summarize: list) -> Optional[str]:
    """Call the LLM to summarize the given messages.

    Uses the unbound chat model (`_original_chat_model`) to avoid tool
    routing during the summarization call.

    Args:
        wm: WorkflowManager instance.
        messages_to_summarize: Messages older than the retention threshold.

    Returns:
        Summary text, or None on failure.
    """
    from langchain_core.messages import HumanMessage, SystemMessage

    chat_model = getattr(wm, "_original_chat_model", None) or getattr(
        wm, "_chat_model", None
    )
    if chat_model is None:
        return None

    conversation_text = _format_messages_for_summary(messages_to_summarize)
    if not conversation_text.strip():
        return None

    prompt = [
        SystemMessage(
            content=(
                "You are a summarization assistant. Summarize the following "
                "conversation excerpt into a concise paragraph that captures "
                "the key topics, decisions, and context. Do not include "
                "greetings or filler. Output only the summary text."
            )
        ),
        HumanMessage(content=conversation_text),
    ]

    try:
        response = chat_model.invoke(prompt)
        return str(getattr(response, "content", response) or "").strip() or None
    except Exception:
        return None


def _format_messages_for_summary(messages: list) -> str:
    """Format a list of LangChain messages as readable text."""
    lines = []
    for msg in messages:
        msg_type = getattr(msg, "type", type(msg).__name__.lower())
        content = getattr(msg, "content", "")
        if not content:
            continue
        role = {"human": "User", "ai": "Assistant", "system": "System"}.get(
            msg_type, msg_type.capitalize()
        )
        lines.append(f"{role}: {content}")
    return "\n".join(lines)
