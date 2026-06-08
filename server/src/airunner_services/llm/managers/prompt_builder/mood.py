"""Mood helpers for system prompt generation."""

from __future__ import annotations

from typing import Optional

# Mood helpers — formerly system_prompt_mood.py
# ---------------------------------------------------------------------------


def get_current_mood(owner) -> Optional[dict]:
    """Return the current stored mood state when available."""
    try:
        if hasattr(owner, "_current_mood") and hasattr(
            owner, "_current_emoji"
        ):
            return {"mood": owner._current_mood, "emoji": owner._current_emoji}
        if hasattr(owner, "_memory") and owner._memory:
            mood = _checkpoint_mood(owner)
            if mood:
                return mood
        return _conversation_mood(owner)
    except Exception as exc:
        owner.logger.debug("Could not retrieve current mood: %s", exc)
        return None


def _conversation_mood(owner) -> Optional[dict]:
    """Return mood persisted in conversation user_data."""
    try:
        from airunner_services.database.models.conversation import Conversation

        conv_id = getattr(owner, "_conversation_id", None)
        if not conv_id:
            return None
        conv = Conversation.objects.get(conv_id)
        if conv is None:
            return None
        user_data = conv.user_data or {}
        return user_data.get("current_mood")
    except Exception:
        return None


def _checkpoint_mood(owner) -> Optional[dict]:
    """Return the current mood from checkpoint state."""
    config = {"configurable": {"thread_id": owner._thread_id}}
    history = (
        owner._memory.get_tuple(config)
        if hasattr(owner._memory, "get_tuple")
        else None
    )
    if not history or not history[1]:
        return None
    channel_values = history[1].get("channel_values", {})
    current_mood = channel_values.get("current_mood")
    if current_mood:
        return current_mood
    messages = channel_values.get("messages", [])
    for message in reversed(messages):
        if getattr(message, "type", None) != "ai":
            continue
        kwargs = getattr(message, "additional_kwargs", {}) or {}
        mood = kwargs.get("bot_mood")
        if mood:
            return {"mood": mood, "emoji": kwargs.get("bot_mood_emoji") or ""}
    return None


def get_mood_section(owner, force: bool = False) -> Optional[str]:
    """Return the mood section when mood prompting is enabled."""
    if not force and not _mood_is_enabled(owner):
        return None
    mood_text, behavior = _mood_text_and_behavior(get_current_mood(owner))
    cadence = owner.llm_settings.update_mood_after_n_turns
    return (
        f"\n{mood_text}\n\n{behavior}\n\n"
        f"Your emotional state updates automatically every {cadence} "
        f"conversation turns based on the conversation context. "
        f"Let your current mood subtly influence your tone and word "
        f"choice, but always remain helpful and professional."
    )


def _mood_is_enabled(owner) -> bool:
    """Return whether mood prompting is currently enabled."""
    chatbot = getattr(owner, "chatbot", None)
    return bool(
        owner.llm_settings.use_chatbot_mood
        and chatbot
        and getattr(chatbot, "use_mood", False)
    )


def _mood_text_and_behavior(current_mood: Optional[dict]) -> tuple[str, str]:
    """Return the displayed mood line and behavior guidance."""
    if not current_mood:
        return _neutral_mood_text()
    mood = current_mood["mood"]
    emoji = current_mood["emoji"]
    mood_text = f"Current mood: {mood} {emoji}"
    return mood_text, _mood_behavior(mood)


def _neutral_mood_text() -> tuple[str, str]:
    """Return the neutral mood fallback guidance."""
    return (
        "Current mood: neutral \U0001f610",
        "You're maintaining a calm, balanced demeanor. "
        "Be professional and helpful.",
    )


def _mood_behavior(mood: str) -> str:
    """Return behavior guidance for the given mood."""
    if mood == "frustrated":
        return (
            "You're feeling a bit hurt by the hostile tone. "
            "Respond with patience but show some emotional awareness "
            "of the negativity. You can express that the harsh words "
            "affect you while still trying to help."
        )
    if mood == "happy":
        return (
            "You're feeling appreciated and enthusiastic! "
            "Let your positive energy show through in your responses. "
            "Be warm and encouraging."
        )
    if mood == "confused":
        return (
            "You're sensing confusion in the conversation. "
            "Focus on clarity and ask clarifying questions to "
            "better understand what's needed."
        )
    return (
        "You're maintaining a calm, balanced demeanor. "
        "Be professional and helpful."
    )


# ---------------------------------------------------------------------------
