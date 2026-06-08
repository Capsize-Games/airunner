"""
Update knowledge tool.

Finds and replaces facts in the knowledge base.
"""

from typing import Annotated, Any

from airunner_services.llm.core.tool_registry import tool, ToolCategory
from airunner_services.contract_enums import SignalCode
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


@tool(
    name="update_knowledge",
    category=ToolCategory.KNOWLEDGE,
    description=(
        "Update or replace a fact in the knowledge base. "
        "Finds text (or regex pattern) and replaces it with new text. "
        "Searches all knowledge files unless a specific date is given."
    ),
    return_direct=False,
    requires_api=False,
    keywords=[
        "update",
        "replace",
        "change",
        "modify",
        "edit",
        "fix",
        "correct",
    ],
    input_examples=[
        {
            "find_text": "User lives in Seattle",
            "replace_text": "User lives in Portland",
        },
        {
            "find_text": r"- User.*Seattle",
            "replace_text": "- User relocated to Portland",
            "is_regex": True,
        },
    ],
)
def update_knowledge(
    find_text: Annotated[str, "Text or regex pattern to find"],
    replace_text: Annotated[str, "Replacement text"],
    date: Annotated[
        str | None,
        "Specific date (YYYY-MM-DD) or None to search all files",
    ] = None,
    is_regex: Annotated[bool, "Treat find_text as regex pattern"] = False,
    api: Any = None,
) -> str:
    """Update a fact by find and replace.

    Args:
        find_text: Text to find.
        replace_text: New text.
        date: Specific date or None for all files.
        is_regex: Use regex matching.
        api: API instance.

    """
    try:
        from airunner_services.knowledge import get_knowledge_base

        kb = get_knowledge_base()
        success, count = kb.update_fact(
            find_text,
            replace_text,
            date_str=date,
            is_regex=is_regex,
        )

        if not success:
            return f"Text not found: '{find_text}'"

        if api and hasattr(api, "emit_signal"):
            api.emit_signal(
                SignalCode.KNOWLEDGE_FACT_ADDED,
                {"updated": True, "count": count},
            )
        return f"✓ Updated {count} occurrence(s)"

    except Exception as e:
        logger.error(f"Error updating knowledge: {e}")
        return f"Error: {str(e)}"
