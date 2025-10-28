"""Knowledge management and memory tools."""

from typing import Callable

from langchain.tools import tool

from airunner.enums import SignalCode
from airunner.components.knowledge.enums import (
    KnowledgeFactCategory,
    KnowledgeSource,
)


class KnowledgeTools:
    """Mixin class providing knowledge and memory management tools."""

    def record_knowledge_tool(self) -> Callable:
        """Record factual knowledge about user or conversation."""

        @tool
        def record_knowledge(
            fact: str,
            category: str = "other",
            tags: str = "",
            confidence: float = 0.9,
        ) -> str:
            """Record important facts about the user or conversation.

            Use this tool to remember important information that comes up in conversations.
            This builds the agent's long-term memory and helps personalize future interactions.

            When to use:
            - User shares personal information (name, location, preferences, etc.)
            - User mentions health conditions, symptoms, or treatments
            - User describes their work, hobbies, or interests
            - User reveals goals, challenges, or important life events
            - User confirms they've already tried something (important for not repeating advice)
            - Any factual information that would be useful to remember

            Args:
                fact: The factual statement to remember (be specific and clear)
                category: Category - one of:
                         USER: user_identity, user_location, user_preferences, user_relationships,
                               user_work, user_interests, user_skills, user_goals, user_history, user_health
                         WORLD: world_knowledge, world_science, world_history, world_geography, world_culture
                         TEMPORAL: temporal_event, temporal_schedule, temporal_reminder, temporal_deadline
                         ENTITY: entity_person, entity_place, entity_organization, entity_product, entity_concept
                         OTHER: relationship, other
                tags: Comma-separated tags for organization (e.g., "chronic,pain,back")
                confidence: How confident you are in this fact (0.0-1.0, default 0.9)

            Returns:
                Confirmation message

            Examples:
                record_knowledge("User's name is Sarah", "user_identity", "name", 1.0)
                record_knowledge("User has chronic back pain", "user_health", "pain,back,chronic", 0.95)
                record_knowledge("User already tried stretching for back pain", "user_history", "back,pain,tried", 0.9)
                record_knowledge("User prefers direct communication style", "user_preferences", "communication", 0.85)
                record_knowledge("Python was created in 1991", "world_history", "python,programming", 0.99)
                record_knowledge("Meeting with John tomorrow at 3pm", "temporal_event", "meeting,john", 0.95)
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
                    try:
                        mapped_cat = (
                            KnowledgeFactCategory.from_legacy_category(
                                category
                            )
                        )
                        category = mapped_cat.value
                        self.logger.info(
                            f"Mapped legacy category '{category}' to '{mapped_cat.value}'"
                        )
                    except (ValueError, KeyError):
                        self.logger.warning(
                            f"Invalid category '{category}', using 'other'"
                        )
                        category = KnowledgeFactCategory.OTHER.value

                # Get conversation ID if available
                conversation_id = None
                if hasattr(self, "current_conversation_id"):
                    conversation_id = self.current_conversation_id

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

                # Emit signal to refresh UI
                self.emit_signal(
                    SignalCode.KNOWLEDGE_FACT_ADDED,
                    {"fact": fact, "category": category},
                )

                return (
                    f"✓ Recorded: {fact[:60]}{'...' if len(fact) > 60 else ''}"
                )
            except Exception as e:
                self.logger.error(f"Error recording knowledge: {e}")
                return f"Error recording knowledge: {str(e)}"

        return record_knowledge

    def recall_knowledge_tool(self) -> Callable:
        """Recall relevant facts from knowledge base."""

        @tool
        def recall_knowledge(query: str, k: int = 5) -> str:
            """Recall relevant facts from long-term memory.

            Use this tool to remember what you know about the user or past conversations.
            This searches through all stored facts using semantic similarity.

            Args:
                query: What you're trying to remember (e.g., "user's health issues")
                k: Number of facts to recall (default 5)

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
                if self.rag_manager and hasattr(
                    self.rag_manager, "embeddings"
                ):
                    embeddings = self.rag_manager.embeddings

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
                        result_parts.append(
                            f"   Tags: {', '.join(fact.tag_list)}"
                        )

                return "\n".join(result_parts)
            except Exception as e:
                self.logger.error(f"Error recalling knowledge: {e}")
                return f"Error recalling knowledge: {str(e)}"

        return recall_knowledge

    def recall_knowledge_by_category_tool(self) -> Callable:
        """Recall facts by category type."""

        @tool
        def recall_knowledge_by_category(
            category_type: str = "user", limit: int = 10
        ) -> str:
            """Recall facts by category type.

            Use this to retrieve facts from specific categories without semantic search.
            Useful when you want to review all facts of a certain type.

            Args:
                category_type: Type of facts to recall - one of:
                              "user" (all user facts)
                              "world" (all world knowledge)
                              "temporal" (all temporal facts)
                              "entity" (all entity facts)
                              "user_health" (specific category)
                              "user_work" (specific category)
                              etc.
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
                    facts = km.get_all_facts(
                        category=category_type, enabled_only=True
                    )
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
                        f"{i}. [{fact.category}] {fact.text} {verified} ({confidence_pct}% confidence)"
                    )
                    if fact.tag_list:
                        result_parts.append(
                            f"   Tags: {', '.join(fact.tag_list)}"
                        )

                return "\n".join(result_parts)
            except Exception as e:
                self.logger.error(
                    f"Error recalling knowledge by category: {e}"
                )
                return f"Error recalling knowledge by category: {str(e)}"

        return recall_knowledge_by_category
