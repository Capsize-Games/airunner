"""Knowledge management and memory tools."""

import logging
from typing import Callable

from langchain.tools import tool

from airunner.enums import SignalCode


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
                category: Category - one of: identity, location, preferences, relationships,
                         work, interests, skills, goals, history, health, other
                tags: Comma-separated tags for organization (e.g., "chronic,pain,back")
                confidence: How confident you are in this fact (0.0-1.0, default 0.9)

            Returns:
                Confirmation message

            Examples:
                record_knowledge("User's name is Sarah", "identity", "name", 1.0)
                record_knowledge("User has chronic back pain", "health", "pain,back,chronic", 0.95)
                record_knowledge("User already tried stretching for back pain", "history", "back,pain,tried", 0.9)
                record_knowledge("User prefers direct communication style", "preferences", "communication", 0.85)
            """
            try:
                from airunner.components.knowledge.knowledge_memory_manager import (
                    KnowledgeMemoryManager,
                )

                # Parse tags
                tag_list = [t.strip() for t in tags.split(",") if t.strip()]

                # Get conversation ID if available
                conversation_id = None
                if hasattr(self, "current_conversation_id"):
                    conversation_id = self.current_conversation_id

                # Create knowledge manager
                km = KnowledgeMemoryManager()

                # Add fact
                km.add_fact(
                    text=fact,
                    category=category,
                    tags=tag_list if tag_list else None,
                    confidence=confidence,
                    source="agent",
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
