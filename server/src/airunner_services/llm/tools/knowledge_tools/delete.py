"""
Delete knowledge tool.

Removes facts from the knowledge base by text or regex match.
"""

from typing import Annotated, Any

from airunner_services.llm.core.tool_registry import tool, ToolCategory
from airunner_services.contract_enums import SignalCode
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


@tool(
    name="delete_knowledge",
    category=ToolCategory.KNOWLEDGE,
    description=(
        "Delete a fact from the knowledge base. "
        "Removes lines containing the specified text (or regex match). "
        "Searches all knowledge files unless a specific date is given."
    ),
    return_direct=False,
    requires_api=False,
    keywords=["delete", "remove", "forget", "erase", "clear"],
    input_examples=[
        {"text": "User lives in Seattle"},
        {"text": r".*outdated fact.*", "is_regex": True},
    ],
)
def delete_knowledge(
    text: Annotated[str, "Text or regex pattern to find and delete"],
    date: Annotated[
        str | None,
        "Specific date (YYYY-MM-DD) or None to search all files",
    ] = None,
    is_regex: Annotated[bool, "Treat text as regex pattern"] = False,
    api: Any = None,
) -> str:
    """Delete facts containing the specified text.

    Args:
        text: Text to find and delete.
        date: Specific date or None for all files.
        is_regex: Use regex matching.
        api: API instance.

    """
    try:
        from airunner_services.knowledge import get_knowledge_base

        kb = get_knowledge_base()
        success, count = kb.delete_fact(
            text,
            date_str=date,
            is_regex=is_regex,
        )

        if not success:
            return f"Text not found: '{text}'"

        if api and hasattr(api, "emit_signal"):
            api.emit_signal(
                SignalCode.KNOWLEDGE_FACT_ADDED,
                {"deleted": True, "count": count},
            )
        return f"✓ Deleted {count} fact(s)"

    except Exception as e:
        logger.error(f"Error deleting knowledge: {e}")
        return f"Error: {str(e)}"
