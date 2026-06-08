"""Memory context helpers and prompt mode detection."""

from __future__ import annotations

from typing import List, Optional

from airunner_services.llm.core.tool_registry import ToolCategory


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
