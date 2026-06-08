"""Part-building helpers for system prompt tiers."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from airunner_services.contract_enums import LLMActionType
from airunner_services.llm.managers.prompt_builder.prompt_builder import (
    CONVERSATIONAL_ACTIONS,
    DATETIME_ACTIONS,
    HEALTH_DISCLAIMER,
    MEMORY_ACTIONS,
    MEMORY_INSTRUCTIONS,
    STYLE_GUIDELINES,
    UI_CONTEXT_ACTIONS,
)
from airunner_services.llm.managers.prompt_builder.mood import (
    get_mood_section,
)


def build_base_prompt_parts(owner, action: LLMActionType) -> list[str]:
    """Return the context-aware prompt parts for one action.

    Selects tier based on remaining context tokens.
    """
    tier = _prompt_tier(owner)
    parts = _identity_parts(owner, action)
    if tier == "base":
        return parts
    _append_if_present(parts, _datetime_part(action))
    _append_if_present(parts, _mood_part(owner, action))
    _append_if_present(parts, _ui_context_part(owner, action))
    _append_if_present(parts, _style_part(action))
    if tier == "standard":
        return parts
    _append_if_present(parts, _memory_part(action))
    _append_if_present(parts, _health_disclaimer_part(owner))
    return parts


def _prompt_tier(owner) -> str:
    """Return the prompt tier based on estimated remaining context tokens."""
    remaining = _estimate_remaining_context_tokens(owner)
    if remaining < 2000:
        return "base"
    if remaining < 4000:
        return "standard"
    return "full"


def _estimate_remaining_context_tokens(owner) -> int:
    """Return remaining token estimate or a large sentinel when unavailable."""
    try:
        wm = getattr(owner, "_workflow_manager", None)
        if wm is None:
            return 999999
        max_tokens = getattr(wm, "_max_history_tokens", 0) or 8000
        memory = getattr(wm, "_memory", None)
        thread_id = getattr(wm, "_thread_id", None)
        if not memory or not thread_id:
            return max_tokens
        state = getattr(memory, "_checkpoint_state", {}).get(thread_id)
        if not state:
            return max_tokens
        messages = state.get("messages", [])
        token_counter = getattr(wm, "_token_counter", None)
        if callable(token_counter) and messages:
            used = token_counter(messages)
        else:
            used = len(messages) * 50
        return max(0, int(max_tokens) - int(used))  # type: ignore[arg-type]
    except Exception:
        return 999999


def _identity_parts(owner, action: LLMActionType) -> list[str]:
    """Return the identity and optional personality prompt parts."""
    chatbot = getattr(owner, "chatbot", None)
    if not chatbot:
        return ["You are a helpful AI assistant."]
    parts = [f"You are {chatbot.botname}, a helpful AI assistant."]
    if action in CONVERSATIONAL_ACTIONS and getattr(
        chatbot, "personality", None
    ):
        parts.append(
            f"Embody the following personality in all your responses. "
            f"Express it through your tone, word choice, and "
            f"conversational style — but never break character or "
            f"make it the topic of conversation unless asked:\n"
            f"{chatbot.personality}"
        )
    return parts


def _datetime_part(action: LLMActionType) -> Optional[str]:
    """Return the datetime prompt part when the action needs it."""
    if action not in DATETIME_ACTIONS:
        return None
    now = datetime.now()
    return f"Current date and time: {now.strftime('%Y-%m-%d %H:%M:%S')}"


def _mood_part(owner, action: LLMActionType) -> Optional[str]:
    """Return the mood prompt part when the action needs it."""
    if action not in CONVERSATIONAL_ACTIONS:
        return None
    return get_mood_section(owner)


def _ui_context_part(owner, action: LLMActionType) -> Optional[str]:
    """Return the UI context prompt part when the action needs it."""
    if action not in UI_CONTEXT_ACTIONS:
        return None
    ui_context = owner._get_ui_section_context()
    return ui_context or None


def _style_part(action: LLMActionType) -> Optional[str]:
    """Return the style prompt part for chat actions."""
    if action == LLMActionType.CHAT:
        return STYLE_GUIDELINES
    return None


def _memory_part(action: LLMActionType) -> Optional[str]:
    """Return the memory prompt part when the action can use memory."""
    if action in MEMORY_ACTIONS:
        return MEMORY_INSTRUCTIONS
    return None


def _health_disclaimer_part(owner) -> Optional[str]:
    """Return the health disclaimer when enabled in settings."""
    settings = getattr(owner, "llm_settings", None)
    if settings is not None and not getattr(
        settings, "include_health_disclaimer", True
    ):
        return None
    return HEALTH_DISCLAIMER


def _append_if_present(parts: list[str], value: Optional[str]) -> None:
    """Append one non-empty prompt part in place."""
    if value:
        parts.append(value)


def augment_custom_system_prompt(
    owner,
    base_prompt: str,
    action: LLMActionType,
    include_mood: Optional[bool] = None,
    include_datetime: Optional[bool] = None,
    include_style: Optional[bool] = None,
    include_memory: Optional[bool] = None,
    include_ui_context: Optional[bool] = None,
) -> str:
    """Append optional Airunner context blocks to a custom prompt."""
    parts = [base_prompt.strip() if base_prompt else ""]
    if _should_include(include_datetime):
        _append_if_present(parts, _datetime_part(action))
    if _should_include(include_mood):
        _append_if_present(parts, get_mood_section(owner, force=True))
    if _should_include(include_ui_context):
        _append_if_present(parts, _ui_context_part(owner, action))
    if _should_include(include_style):
        _append_if_present(parts, _style_part(action))
    if _should_include(include_memory):
        _append_if_present(parts, _memory_part(action))
    return "\n\n".join(part for part in parts if part)


def _should_include(flag: Optional[bool]) -> bool:
    """Return whether a custom prompt flag enables an optional block."""
    return flag is True


def build_research_mode_prompt(owner) -> str:
    """Return the focused deep-research system prompt."""
    chatbot = getattr(owner, "chatbot", None)
    if chatbot:
        identity = (
            f"You are {chatbot.botname}, a research assistant performing "
            f"deep research."
        )
    else:
        identity = "You are a research assistant performing deep research."
    now = datetime.now()
    datetime_line = (
        f"Current date and time: {now.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    instruction = (
        "You are in DEEP RESEARCH MODE. Your sole focus is completing "
        "the research workflow.\nIGNORE any UI context or dashboard "
        "information - focus ONLY on the research task.\nContinue "
        "calling tools until the research is complete."
    )
    return "\n\n".join([identity, datetime_line, instruction])


def build_system_prompt_for_action(owner, action: LLMActionType) -> str:
    """Return the base system prompt for one action."""
    return "\n\n".join(build_base_prompt_parts(owner, action))


# ---------------------------------------------------------------------------
