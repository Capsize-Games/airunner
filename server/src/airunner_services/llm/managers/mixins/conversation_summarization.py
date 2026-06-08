"""In-context conversation summarization triggered after each generation turn."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    pass


def maybe_summarize_checkpoint(owner: Any) -> None:
    """Compress old messages in the checkpoint when threshold exceeded."""
    try:
        perform_summary, threshold = _read_settings(owner)
        if not perform_summary or not threshold or threshold <= 0:
            return
        messages, state, ckpt_state, thread_id = _get_checkpoint(owner)
        if messages is None or len(messages) <= threshold:
            return
        owner.logger.info(
            "[SUMMARIZE] %d messages > threshold %d — compressing",
            len(messages),
            threshold,
        )
        summary = _call_llm_for_summary(
            getattr(owner, "_workflow_manager", None),
            messages[:-threshold],
        )
        if not summary:
            owner.logger.warning(
                "[SUMMARIZE] LLM returned empty summary, skipping"
            )
            return
        _compress_checkpoint(
            messages, threshold, summary, state, ckpt_state, thread_id, owner
        )
    except Exception as exc:
        try:
            owner.logger.warning(
                "[SUMMARIZE] Error during summarization: %s", exc
            )
        except Exception:
            pass


def _read_settings(owner: Any) -> tuple[Any, int]:
    """Return (perform_summary, threshold) from DB or dataclass."""
    db = getattr(owner, "llm_generator_settings", None)
    perform_summary = (
        getattr(db, "perform_conversation_summary", None) if db else None
    )
    threshold = getattr(db, "summarize_after_n_turns", None) if db else None
    settings = getattr(owner, "llm_settings", None)
    if settings is not None:
        if perform_summary is None:
            perform_summary = getattr(
                settings, "perform_conversation_summary", False
            )
        if threshold is None or threshold <= 0:
            threshold = getattr(settings, "summarize_after_n_turns", 0)
    return perform_summary, threshold


def _get_checkpoint(owner: Any) -> tuple:
    """Return (messages, state, ckpt_state, thread_id) or (None,)*4."""
    wm = getattr(owner, "_workflow_manager", None)
    if wm is None:
        return None, None, None, None
    memory = getattr(wm, "_memory", None)
    thread_id = getattr(wm, "_thread_id", None)
    if memory is None or thread_id is None:
        return None, None, None, None
    ckpt_state = getattr(memory, "_checkpoint_state", {})
    state = ckpt_state.get(thread_id)
    if not state:
        return None, None, None, None
    return state.get("messages", []), state, ckpt_state, thread_id


def _compress_checkpoint(
    messages: list,
    threshold: int,
    summary: str,
    state: dict,
    ckpt_state: dict,
    thread_id: str,
    owner: Any,
) -> None:
    """Replace old messages with a SystemMessage summary in checkpoint."""
    from langchain_core.messages import SystemMessage

    summary_msg = SystemMessage(
        content=f"[Conversation summary — older messages compressed]\n{summary}"
    )
    new_messages = [summary_msg] + list(messages[-threshold:])
    state["messages"] = new_messages
    cp = state.get("checkpoint", {})
    cv = cp.get("channel_values", {})
    cv["messages"] = new_messages
    cp["channel_values"] = cv
    state["checkpoint"] = cp
    ckpt_state[thread_id] = state
    owner.logger.info(
        "[SUMMARIZE] Compressed %d → %d messages",
        len(messages),
        len(new_messages),
    )


def _call_llm_for_summary(
    wm: Any, messages_to_summarize: list
) -> Optional[str]:
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
        return (
            str(getattr(response, "content", response) or "").strip() or None
        )
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
