"""
Knowledge management tools.

Tools for recording, recalling, updating, and deleting facts from the
knowledge base. Facts are stored in daily markdown files and indexed
for semantic (RAG) retrieval.

Knowledge files are stored in ~/.local/share/airunner/text/knowledge/
with one file per day (YYYY-MM-DD.md format).
"""

from typing import Annotated, Any

from airunner.components.llm.core.tool_registry import tool, ToolCategory
from airunner.enums import SignalCode
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


@tool(
    name="record_knowledge",
    category=ToolCategory.KNOWLEDGE,
    description=(
        "Record a fact about the user or something learned. Facts are stored "
        "in daily markdown files organized by section. Each fact is separated "
        "by blank lines for easy reading and editing. "
        "Sections: Identity, Work & Projects, Interests & Hobbies, "
        "Preferences, Health & Wellness, Relationships, Goals, Notes."
    ),
    return_direct=False,
    requires_api=True,
    defer_loading=False,  # Essential tool - always available
    keywords=["remember", "memory", "fact", "store", "save", "learn", "record", "note"],
    input_examples=[
        {"fact": "User's name is Joe Curlee", "section": "Identity"},
        {"fact": "User has chronic back pain", "section": "Health & Wellness"},
        {"fact": "User is working on AI Runner project", "section": "Work & Projects"},
        {"fact": "User prefers dark mode", "section": "Preferences"},
    ],
)
def record_knowledge(
    fact: Annotated[str, "The factual statement to remember"],
    section: Annotated[
        str,
        (
            "Section: Identity, Work & Projects, Interests & Hobbies, "
            "Preferences, Health & Wellness, Relationships, Goals, or Notes"
        ),
    ] = "Notes",
    api: Any = None,
) -> str:
    """Record a fact to the knowledge base.

    Facts are stored in today's knowledge file under the specified section.
    Each fact is separated by blank lines for easy parsing.

    Args:
        fact: The fact to record
        section: Which section to add it to
        api: API instance (injected)

    """
    try:
        from airunner.components.knowledge.knowledge_base import get_knowledge_base

        kb = get_knowledge_base()
        success = kb.add_fact(fact, section=section)

        if success:
            if api and hasattr(api, "emit_signal"):
                api.emit_signal(
                    SignalCode.KNOWLEDGE_FACT_ADDED,
                    {"fact": fact, "section": section},
                )
            return f"✓ Recorded in {section}: {fact[:60]}{'...' if len(fact) > 60 else ''}"
        else:
            # Check if it's a duplicate vs section not found
            if section in ["Identity", "Work & Projects", "Interests & Hobbies", 
                          "Preferences", "Health & Wellness", "Relationships", 
                          "Goals", "Notes"]:
                return f"⚡ Already known (skipped duplicate): {fact[:50]}..."
            return f"Failed to record fact. Section '{section}' may not exist."

    except Exception as e:
        logger.error(f"Error recording knowledge: {e}")
        return f"Error: {str(e)}"


@tool(
    name="recall_knowledge",
    category=ToolCategory.KNOWLEDGE,
    description=(
        "Search the knowledge base for relevant facts. Uses semantic search "
        "(RAG) to find facts related to the query across all stored knowledge."
    ),
    return_direct=False,
    requires_api=True,
    defer_loading=False,  # Essential tool - always available
    keywords=["remember", "memory", "recall", "search", "find", "know", "what do I know"],
    input_examples=[
        {"query": "user's health conditions"},
        {"query": "what projects is the user working on"},
        {"query": "user's name and location"},
        {"query": "user's hobbies"},
    ],
)
def recall_knowledge(
    query: Annotated[str, "What you're trying to remember or find"],
    max_results: Annotated[int, "Maximum facts to return"] = 5,
    api: Any = None,
) -> str:
    """Search the knowledge base for relevant facts.

    Uses semantic search to find facts matching the query across all
    stored knowledge files.

    Args:
        query: What to search for
        max_results: Max results to return
        api: API instance (injected)

    """
    try:
        from airunner.components.knowledge.knowledge_base import get_knowledge_base

        kb = get_knowledge_base()
        
        # Try RAG search first - api is the agent with RAGMixin
        agent = api if api and hasattr(api, 'search') else None
        results = kb.search_rag(query, k=max_results, agent=agent)
        
        if not results:
            # Fallback to keyword search
            keyword_results = kb.search(query, max_results=max_results)
            results = [r['line'] for r in keyword_results]
        
        if not results:
            return (
                f"No knowledge found for: '{query}'.\n\n"
                "**ACTION REQUIRED:** You MUST now use search_news or search_web to find this information. "
                "Do NOT tell the user to search elsewhere - use the tools available to you."
            )

        output = f"Found {len(results)} relevant fact(s):\n\n"
        for i, fact in enumerate(results, 1):
            output += f"{i}. {fact}\n"
        
        output += (
            "\n**IMPORTANT:** If these facts don't directly answer the user's question, "
            "you MUST use search_news or search_web to find current information. "
            "Do NOT tell the user to search elsewhere."
        )
        
        return output

    except Exception as e:
        logger.error(f"Error recalling knowledge: {e}")
        return f"Error: {str(e)}"


@tool(
    name="read_knowledge_file",
    category=ToolCategory.KNOWLEDGE,
    description=(
        "Read a specific day's knowledge file or all recent knowledge. "
        "Use this to review what's already recorded before adding new facts."
    ),
    return_direct=False,
    requires_api=False,
    keywords=["read", "view", "show", "list", "knowledge", "file", "today"],
    input_examples=[
        {"date": None},  # Today
        {"date": "2025-11-28"},  # Specific date
        {"read_all": True},  # All recent files
    ],
)
def read_knowledge_file(
    date: Annotated[
        str,
        "Date in YYYY-MM-DD format, or leave empty for today"
    ] = None,
    read_all: Annotated[
        bool,
        "If True, read all recent knowledge files combined"
    ] = False,
) -> str:
    """Read knowledge from a specific date or all recent files.

    Args:
        date: Specific date (YYYY-MM-DD) or None for today
        read_all: If True, combine all recent knowledge files

    """
    try:
        from airunner.components.knowledge.knowledge_base import get_knowledge_base

        kb = get_knowledge_base()
        
        if read_all:
            content = kb.read_all(max_files=30)
        else:
            content = kb.read_file(date)
        
        if not content or not content.strip():
            if date:
                return f"No knowledge file found for {date}"
            else:
                return "No knowledge recorded yet for today. Use record_knowledge to add facts."
        
        return content

    except Exception as e:
        logger.error(f"Error reading knowledge: {e}")
        return f"Error: {str(e)}"


@tool(
    name="update_knowledge",
    category=ToolCategory.KNOWLEDGE,
    description=(
        "Update or replace a fact in the knowledge base. "
        "Finds text (or regex pattern) and replaces it with new text. "
        "Searches all knowledge files unless a specific date is given."
    ),
    return_direct=False,
    requires_api=True,
    keywords=["update", "replace", "change", "modify", "edit", "fix", "correct"],
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
        str,
        "Specific date (YYYY-MM-DD) or None to search all files"
    ] = None,
    is_regex: Annotated[bool, "Treat find_text as regex pattern"] = False,
    api: Any = None,
) -> str:
    """Update a fact by find and replace.

    Args:
        find_text: Text to find
        replace_text: New text
        date: Specific date or None for all files
        is_regex: Use regex matching
        api: API instance

    """
    try:
        from airunner.components.knowledge.knowledge_base import get_knowledge_base

        kb = get_knowledge_base()
        success, count = kb.update_fact(
            find_text, replace_text, date_str=date, is_regex=is_regex
        )

        if success:
            if api and hasattr(api, "emit_signal"):
                api.emit_signal(
                    SignalCode.KNOWLEDGE_FACT_ADDED,
                    {"updated": True, "count": count},
                )
            return f"✓ Updated {count} occurrence(s)"
        else:
            return f"Text not found: '{find_text}'"

    except Exception as e:
        logger.error(f"Error updating knowledge: {e}")
        return f"Error: {str(e)}"


@tool(
    name="delete_knowledge",
    category=ToolCategory.KNOWLEDGE,
    description=(
        "Delete a fact from the knowledge base. "
        "Removes lines containing the specified text (or regex match). "
        "Searches all knowledge files unless a specific date is given."
    ),
    return_direct=False,
    requires_api=True,
    keywords=["delete", "remove", "forget", "erase", "clear"],
    input_examples=[
        {"text": "User lives in Seattle"},
        {"text": r".*outdated fact.*", "is_regex": True},
    ],
)
def delete_knowledge(
    text: Annotated[str, "Text or regex pattern to find and delete"],
    date: Annotated[
        str,
        "Specific date (YYYY-MM-DD) or None to search all files"
    ] = None,
    is_regex: Annotated[bool, "Treat text as regex pattern"] = False,
    api: Any = None,
) -> str:
    """Delete facts containing the specified text.

    Args:
        text: Text to find and delete
        date: Specific date or None for all files
        is_regex: Use regex matching
        api: API instance

    """
    try:
        from airunner.components.knowledge.knowledge_base import get_knowledge_base

        kb = get_knowledge_base()
        success, count = kb.delete_fact(text, date_str=date, is_regex=is_regex)

        if success:
            if api and hasattr(api, "emit_signal"):
                api.emit_signal(
                    SignalCode.KNOWLEDGE_FACT_ADDED,
                    {"deleted": True, "count": count},
                )
            return f"✓ Deleted {count} fact(s)"
        else:
            return f"Text not found: '{text}'"

    except Exception as e:
        logger.error(f"Error deleting knowledge: {e}")
        return f"Error: {str(e)}"


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
    """List all knowledge files.

    """
    try:
        from airunner.components.knowledge.knowledge_base import get_knowledge_base

        kb = get_knowledge_base()
        files = kb.list_files()

        if not files:
            return "No knowledge files found. Use record_knowledge to start recording facts."

        output = f"Knowledge files ({len(files)} total):\n\n"
        for f in files[:20]:  # Show max 20
            size = f.stat().st_size
            output += f"• {f.stem} ({size} bytes)\n"
        
        if len(files) > 20:
            output += f"\n... and {len(files) - 20} more files"

        return output

    except Exception as e:
        logger.error(f"Error listing files: {e}")
        return f"Error: {str(e)}"
