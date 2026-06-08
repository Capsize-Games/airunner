"""Context-aware tiered prompt assembly and action mapping."""

from __future__ import annotations

from typing import List, Optional

from airunner_services.contract_enums import LLMActionType
from airunner_services.llm.core.tool_registry import ToolCategory

# Context-aware tiered prompt assembly — formerly system_prompt_context.py
# ---------------------------------------------------------------------------


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
    """Return the context-aware prompt parts for one action.

    Selects tier based on remaining context tokens: base (<2000), standard (<4000), full (otherwise).
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
    """Estimate how many tokens remain in the context window."""
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
