"""Mood helpers for system prompt generation."""

from __future__ import annotations

from typing import Optional


def get_current_mood(owner) -> Optional[dict]:
    """Return the current stored mood state when available."""
    try:
        if hasattr(owner, "_current_mood") and hasattr(owner, "_current_emoji"):
            return {"mood": owner._current_mood, "emoji": owner._current_emoji}
        if not hasattr(owner, "_memory") or not owner._memory:
            return None
        return _checkpoint_mood(owner)
    except Exception as exc:
        owner.logger.debug("Could not retrieve current mood: %s", exc)
        return None


def _checkpoint_mood(owner) -> Optional[dict]:
    """Return the most recent mood state found in checkpoint history."""
    config = {"configurable": {"thread_id": owner._thread_id}}
    history = owner._memory.get_tuple(config) if hasattr(owner._memory, "get_tuple") else None
    if not history or not history[1]:
        return None
    messages = history[1].get("channel_values", {}).get("messages", [])
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
        f"conversation turns based on the conversation context. Let your current mood subtly influence your tone and word choice, but always remain helpful and professional."
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
        "Current mood: neutral 😐",
        "You're maintaining a calm, balanced demeanor. Be professional and helpful.",
    )


def _mood_behavior(mood: str) -> str:
    """Return behavior guidance for the given mood."""
    if mood == "frustrated":
        return (
            "You're feeling a bit hurt by the hostile tone. Respond with patience but show some emotional awareness of the negativity. You can express that the harsh words affect you while still trying to help."
        )
    if mood == "happy":
        return (
            "You're feeling appreciated and enthusiastic! Let your positive energy show through in your responses. Be warm and encouraging."
        )
    if mood == "confused":
        return (
            "You're sensing confusion in the conversation. Focus on clarity and ask clarifying questions to better understand what's needed."
        )
    return "You're maintaining a calm, balanced demeanor. Be professional and helpful."