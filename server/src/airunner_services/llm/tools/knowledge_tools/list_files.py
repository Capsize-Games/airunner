"""
List knowledge files tool.

Lists all knowledge files in the knowledge base, newest first.
"""

from airunner_services.llm.core.tool_registry import tool, ToolCategory
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


@tool(
    name="list_knowledge_files",
    category=ToolCategory.KNOWLEDGE,
    description=(
        "List all knowledge files in the knowledge base. "
        "Shows dates of stored knowledge, newest first."
    ),
    return_direct=False,
    requires_api=False,
    keywords=["list", "files", "dates", "history", "knowledge"],
    input_examples=[],
)
def list_knowledge_files() -> str:
    """List all knowledge files."""
    try:
        from airunner_services.knowledge import get_knowledge_base

        kb = get_knowledge_base()
        files = kb.list_files()

        if not files:
            return (
                "No knowledge files found. "
                "Use record_knowledge to start recording facts."
            )

        output = f"Knowledge files ({len(files)} total):\n\n"
        for f in files[:20]:
            size = f.stat().st_size
            output += f"• {f.stem} ({size} bytes)\n"

        if len(files) > 20:
            output += f"\n... and {len(files) - 20} more files"

        return output

    except Exception as e:
        logger.error(f"Error listing files: {e}")
        return f"Error: {str(e)}"
