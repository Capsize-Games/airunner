"""
Record knowledge tool.

Stores a fact in the knowledge base under a specified section.
"""

from typing import Annotated, Any

from airunner_services.llm.core.tool_registry import tool, ToolCategory
from airunner_services.contract_enums import SignalCode
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

VALID_SECTIONS = [
    "Identity",
    "Work & Projects",
    "Interests & Hobbies",
    "Preferences",
    "Health & Wellness",
    "Relationships",
    "Goals",
    "Notes",
]


@tool(
    name="record_knowledge",
    category=ToolCategory.KNOWLEDGE,
    description=(
        "Record a fact about the user or something learned. Facts are "
        "stored in daily markdown files organized by section. Each fact "
        "is separated by blank lines for easy reading and editing. "
        "Sections: Identity, Work & Projects, Interests & Hobbies, "
        "Preferences, Health & Wellness, Relationships, Goals, Notes."
    ),
    return_direct=False,
    requires_api=False,
    defer_loading=False,
    keywords=[
        "remember",
        "memory",
        "fact",
        "store",
        "save",
        "learn",
        "record",
        "note",
    ],
    input_examples=[
        {"fact": "User's name is Joe Curlee", "section": "Identity"},
        {"fact": "User has chronic back pain", "section": "Health & Wellness"},
        {
            "fact": "User is working on AI Runner project",
            "section": "Work & Projects",
        },
        {"fact": "User prefers dark mode", "section": "Preferences"},
    ],
)
def record_knowledge(
    fact: Annotated[str, "The factual statement to remember"],
    section: Annotated[
        str,
        (
            "Section: Identity, Work & Projects, Interests & Hobbies, "
            "Preferences, Health & Wellness, Relationships, Goals, "
            "or Notes"
        ),
    ] = "Notes",
    api: Any = None,
) -> str:
    """Record a fact to the knowledge base.

    Facts are stored in today's knowledge file under the specified
    section. Each fact is separated by blank lines for easy parsing.

    Args:
        fact: The fact to record.
        section: Which section to add it to.
        api: API instance (injected).

    """
    try:
        from airunner_services.knowledge import get_knowledge_base

        kb = get_knowledge_base()
        success = kb.add_fact(fact, section=section)

        if not success:
            if section in VALID_SECTIONS:
                return (
                    f"⚡ Already known (skipped duplicate): " f"{fact[:50]}..."
                )
            return (
                f"Failed to record fact. "
                f"Section '{section}' may not exist."
            )

        if api and hasattr(api, "emit_signal"):
            api.emit_signal(
                SignalCode.KNOWLEDGE_FACT_ADDED,
                {"fact": fact, "section": section},
            )
        return (
            f"✓ Recorded in {section}: "
            f"{fact[:60]}{'...' if len(fact) > 60 else ''}"
        )

    except Exception as e:
        logger.error(f"Error recording knowledge: {e}")
        return f"Error: {str(e)}"
