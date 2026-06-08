"""
Read knowledge file tool.

Reads a specific day's knowledge file or all recent knowledge.
"""

from typing import Annotated

from airunner_services.llm.core.tool_registry import tool, ToolCategory
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


@tool(
    name="read_knowledge_file",
    category=ToolCategory.KNOWLEDGE,
    description=(
        "Read a specific day's knowledge file or all recent knowledge. "
        "Use this to review what's already recorded before adding new "
        "facts."
    ),
    return_direct=False,
    requires_api=False,
    keywords=[
        "read",
        "view",
        "show",
        "list",
        "knowledge",
        "file",
        "today",
    ],
    input_examples=[
        {"date": None},  # Today
        {"date": "2025-11-28"},  # Specific date
        {"read_all": True},  # All recent files
    ],
)
def read_knowledge_file(
    date: Annotated[
        str | None, "Date in YYYY-MM-DD format, or leave empty for today"
    ] = None,
    read_all: Annotated[
        bool, "If True, read all recent knowledge files combined"
    ] = False,
) -> str:
    """Read knowledge from a specific date or all recent files.

    Args:
        date: Specific date (YYYY-MM-DD) or None for today.
        read_all: If True, combine all recent knowledge files.

    """
    try:
        from airunner_services.knowledge import get_knowledge_base

        kb = get_knowledge_base()

        if read_all:
            content = kb.read_all(max_files=30)
        else:
            content = kb.read_file(date)

        if not content or not content.strip():
            if date:
                return f"No knowledge file found for {date}"
            return (
                "No knowledge recorded yet for today. "
                "Use record_knowledge to add facts."
            )

        return content

    except Exception as e:
        logger.error(f"Error reading knowledge: {e}")
        return f"Error: {str(e)}"
