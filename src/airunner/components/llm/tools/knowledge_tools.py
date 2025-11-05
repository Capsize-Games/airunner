"""
Knowledge management and memory tools.

Tools for recording facts, recalling knowledge, and managing long-term memory.
"""

import logging
from typing import Annotated, Any

from airunner.components.llm.core.tool_registry import tool, ToolCategory
from airunner.enums import SignalCode
from airunner.components.knowledge.enums import (
    KnowledgeFactCategory,
    KnowledgeSource,
)

logger = logging.getLogger(__name__)


@tool(
    name="record_knowledge",
    category=ToolCategory.RAG,
    description=(
        "Record important facts about the user or conversation. "
        "This builds the agent's long-term memory and helps personalize "
        "future interactions. Use when user shares personal information, "
        "preferences, health conditions, or any factual information "
        "that would be useful to remember."
    ),
    return_direct=False,
    requires_api=True,
)
def record_knowledge(
    fact: Annotated[
        str, "The factual statement to remember (be specific and clear)"
    ],
    category: Annotated[
        str,
        (
            "Category - one of: user_identity, user_location, "
            "user_preferences, user_relationships, user_work, user_interests, "
            "user_skills, user_goals, user_history, user_health, "
            "world_knowledge, world_science, world_history, world_geography, "
            "world_culture, temporal_event, temporal_schedule, "
            "temporal_reminder, temporal_deadline, entity_person, "
            "entity_place, entity_organization, entity_product, "
            "entity_concept, relationship, other"
        ),
    ] = "other",
    tags: Annotated[
        str,
        "Comma-separated tags for organization (e.g., 'chronic,pain,back')",
    ] = "",
    confidence: Annotated[
        float, "How confident you are in this fact (0.0-1.0)"
    ] = 0.9,
    api: Any = None,
) -> str:
    """Record important facts about the user or conversation.

    Use this tool to remember important information that comes up in
    conversations. This builds the agent's long-term memory and helps
    personalize future interactions.

    When to use:
    - User shares personal information (name, location, preferences, etc.)
    - User mentions health conditions, symptoms, or treatments
    - User describes their work, hobbies, or interests
    - User reveals goals, challenges, or important life events
    - User confirms they've already tried something
    - Any factual information that would be useful to remember

    Args:
        fact: The factual statement to remember
        category: Category for organization
        tags: Comma-separated tags
        confidence: Confidence in this fact (0.0-1.0, default 0.9)
        api: API instance (injected)

    Returns:
        Confirmation message

    Examples:
        record_knowledge("User's name is Sarah", "user_identity", "name", 1.0)
        record_knowledge("User has chronic back pain", "user_health",
                        "pain,back,chronic", 0.95)
        record_knowledge("User already tried stretching for back pain",
                        "user_history", "back,pain,tried", 0.9)
        record_knowledge("User prefers direct communication style",
                        "user_preferences", "communication", 0.85)
    """
    try:
        from airunner.components.knowledge.knowledge_memory_manager import (
            KnowledgeMemoryManager,
        )

        # Parse tags
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]

        # Validate and map category
        valid_categories = [cat.value for cat in KnowledgeFactCategory]
        if category not in valid_categories:
            # Try legacy category mapping
            original_category = category
            try:
                mapped_cat = KnowledgeFactCategory.from_legacy_category(
                    category
                )
                category = mapped_cat.value
                logger.info(
                    f"Mapped legacy category '{original_category}' to "
                    f"'{mapped_cat.value}'"
                )
            except (ValueError, KeyError):
                logger.warning(
                    f"Invalid category '{original_category}', using 'other'"
                )
                category = KnowledgeFactCategory.OTHER.value

        # Get conversation ID if available
        conversation_id = None
        if api and hasattr(api, "current_conversation_id"):
            conversation_id = api.current_conversation_id

        # Create knowledge manager
        km = KnowledgeMemoryManager()

        # Add fact with proper source enum
        km.add_fact(
            text=fact,
            category=category,
            tags=tag_list if tag_list else None,
            confidence=confidence,
            source=KnowledgeSource.CONVERSATION.value,
            conversation_id=conversation_id,
            verified=False,
        )

        # Emit signal to refresh UI if API available
        if api and hasattr(api, "emit_signal"):
            api.emit_signal(
                SignalCode.KNOWLEDGE_FACT_ADDED,
                {"fact": fact, "category": category},
            )

        return f"✓ Recorded: {fact[:60]}{'...' if len(fact) > 60 else ''}"
    except Exception as e:
        logger.error(f"Error recording knowledge: {e}")
        return f"Error recording knowledge: {str(e)}"


@tool(
    name="recall_knowledge",
    category=ToolCategory.RAG,
    description=(
        "Recall relevant facts from long-term memory. "
        "Use this to remember what you know about the user or past "
        "conversations. Searches through all stored facts using "
        "semantic similarity."
    ),
    return_direct=False,
    requires_api=True,
)
def recall_knowledge(
    query: Annotated[
        str,
        "What you're trying to remember (e.g., \"user's health issues\")",
    ],
    k: Annotated[int, "Number of facts to recall"] = 5,
    api: Any = None,
) -> str:
    """Recall relevant facts from long-term memory.

    Use this tool to remember what you know about the user or past
    conversations. This searches through all stored facts using semantic
    similarity.

    Args:
        query: What you're trying to remember
        k: Number of facts to recall (default 5)
        api: API instance (injected)

    Returns:
        Relevant facts or message if none found

    Examples:
        recall_knowledge("user's health conditions")
        recall_knowledge("what has the user already tried for pain")
        recall_knowledge("user's hobbies and interests")
    """
    try:
        from airunner.components.knowledge.knowledge_memory_manager import (
            KnowledgeMemoryManager,
        )

        # Create knowledge manager with embeddings
        embeddings = None
        if api:
            rag_manager = getattr(api, "rag_manager", None)
            if rag_manager and hasattr(rag_manager, "embeddings"):
                embeddings = rag_manager.embeddings

        km = KnowledgeMemoryManager(embeddings=embeddings)

        # Recall facts
        facts = km.recall_facts(query, k=k)

        if not facts:
            return f"No relevant knowledge found for: {query}"

        # Format response
        result_parts = [f"Recalled {len(facts)} relevant fact(s):\n"]
        for i, fact in enumerate(facts, 1):
            verified = "✓" if fact.verified else ""
            confidence_pct = int(fact.confidence * 100)
            result_parts.append(
                f"{i}. {fact.text} {verified} ({confidence_pct}% confidence)"
            )
            if fact.tag_list:
                result_parts.append(f"   Tags: {', '.join(fact.tag_list)}")

        return "\n".join(result_parts)
    except Exception as e:
        logger.error(f"Error recalling knowledge: {e}")
        return f"Error recalling knowledge: {str(e)}"


@tool(
    name="recall_knowledge_by_category",
    category=ToolCategory.RAG,
    description=(
        "Recall facts by category type without semantic search. "
        "Useful when you want to review all facts of a certain type. "
        "Categories include: user, world, temporal, entity, or specific "
        "subcategories like user_health, user_work, etc."
    ),
    return_direct=False,
    requires_api=False,
)
def recall_knowledge_by_category(
    category_type: Annotated[
        str,
        (
            "Type of facts to recall - one of: user, world, temporal, entity, "
            "user_health, user_work, temporal_event, etc."
        ),
    ] = "user",
    limit: Annotated[int, "Maximum number of facts to return"] = 10,
) -> str:
    """Recall facts by category type.

    Use this to retrieve facts from specific categories without semantic
    search. Useful when you want to review all facts of a certain type.

    Args:
        category_type: Type of facts to recall
        limit: Maximum number of facts to return (default 10)

    Returns:
        Formatted list of facts or message if none found

    Examples:
        recall_knowledge_by_category("user")  # All user facts
        recall_knowledge_by_category("user_health", 5)  # Up to 5 health facts
        recall_knowledge_by_category("temporal")  # All temporal facts
        recall_knowledge_by_category("world")  # All world knowledge
    """
    try:
        from airunner.components.knowledge.knowledge_memory_manager import (
            KnowledgeMemoryManager,
        )

        km = KnowledgeMemoryManager()

        # Determine if this is a type filter or specific category
        category_types = ["user", "world", "temporal", "entity"]

        if category_type in category_types:
            # Filter by category type
            kwargs = {f"is_{category_type}": True}
            facts = km.get_facts_by_category_type(**kwargs)

            # Limit results
            facts = facts[:limit] if facts else []
            type_label = category_type.title()
        else:
            # Filter by specific category
            facts = km.get_all_facts(category=category_type, enabled_only=True)
            facts = facts[:limit] if facts else []
            type_label = category_type.replace("_", " ").title()

        if not facts:
            return f"No {type_label} facts found"

        # Format response
        result_parts = [f"Found {len(facts)} {type_label} fact(s):\n"]
        for i, fact in enumerate(facts, 1):
            verified = "✓" if fact.verified else ""
            confidence_pct = int(fact.confidence * 100)
            result_parts.append(
                f"{i}. [{fact.category}] {fact.text} {verified} "
                f"({confidence_pct}% confidence)"
            )
            if fact.tag_list:
                result_parts.append(f"   Tags: {', '.join(fact.tag_list)}")

        return "\n".join(result_parts)
    except Exception as e:
        logger.error(f"Error recalling knowledge by category: {e}")
        return f"Error recalling knowledge by category: {str(e)}"
