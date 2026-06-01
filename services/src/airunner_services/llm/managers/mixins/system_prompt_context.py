"""Context and prompt-building helpers for system prompt generation."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from airunner_services.contract_enums import LLMActionType
from airunner_services.llm.core.tool_registry import ToolCategory
from airunner_services.llm.managers.mixins.system_prompt_mood import (
    get_current_mood,
    get_mood_section,
)
from airunner_services.llm.managers.mixins.system_prompt_text import (
    CONVERSATIONAL_ACTIONS,
    DATETIME_ACTIONS,
    MEMORY_ACTIONS,
    MEMORY_INSTRUCTIONS,
    STYLE_GUIDELINES,
    UI_CONTEXT_ACTIONS,
)


def get_memory_context(owner, user_query: Optional[str] = None) -> str:
    """Return relevant user memory context when available."""
    try:
        from airunner_services.knowledge import get_knowledge_base

        kb = get_knowledge_base()
        if user_query:
            return _search_memory_context(kb, user_query)
        return kb.get_context(max_chars=2000) or ""
    except Exception:
        return ""


def _search_memory_context(kb, user_query: str) -> str:
    """Return one formatted knowledge block from RAG results."""
    results = kb.search_rag(user_query, k=10)
    if not results:
        return ""
    lines = ["## Relevant Knowledge", ""]
    lines.extend(f"- {result}" for result in results)
    return "\n".join(lines)


def get_prompt_mode(tool_categories: Optional[List] = None) -> str:
    """Return the prompt mode for the given tool categories."""
    if not tool_categories:
        return "conversational"
    categories = _normalize_tool_categories(tool_categories)
    if ToolCategory.MATH in categories:
        return "math"
    if ToolCategory.ANALYSIS in categories:
        return "precision"
    return "conversational"


def _normalize_tool_categories(tool_categories: List) -> list:
    """Normalize string and enum tool categories to enum values."""
    category_values = []
    for category in tool_categories:
        if isinstance(category, str):
            category_values.extend(
                tool_category
                for tool_category in ToolCategory
                if tool_category.value == category
            )
            continue
        category_values.append(category)
    return category_values


def build_base_prompt_parts(owner, action: LLMActionType) -> List[str]:
    """Return the context-aware prompt parts for one action."""
    parts = _identity_parts(owner, action)
    _append_if_present(parts, _datetime_part(action))
    _append_if_present(parts, _mood_part(owner, action))
    _append_if_present(parts, _ui_context_part(owner, action))
    _append_if_present(parts, _style_part(action))
    _append_if_present(parts, _memory_part(action))
    return parts


def _identity_parts(owner, action: LLMActionType) -> list[str]:
    """Return the identity and optional personality prompt parts."""
    chatbot = getattr(owner, "chatbot", None)
    if not chatbot:
        return ["You are a helpful AI assistant."]
    parts = [f"You are {chatbot.botname}, a helpful AI assistant."]
    if action in CONVERSATIONAL_ACTIONS and getattr(chatbot, "personality", None):
        parts.append(f"Personality: {chatbot.personality}")
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
    datetime_line = f"Current date and time: {now.strftime('%Y-%m-%d %H:%M:%S')}"
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