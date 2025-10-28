"""
Working memory system for knowledge management.

Maintains a cache of recently extracted facts for quick access and
context injection into LLM prompts.
"""

import logging
from collections import OrderedDict
from datetime import datetime
from typing import List, Optional, Dict, Any

from airunner.components.knowledge.knowledge_memory_manager import (
    KnowledgeMemoryManager,
)
from airunner.components.knowledge.data.models import KnowledgeFact


class WorkingMemory:
    """
    Working memory cache for recently accessed knowledge facts.

    Maintains an LRU cache of the most recent/important facts for
    fast context injection without database queries.

    Attributes:
        max_size: Maximum number of facts to keep in cache
        cache: OrderedDict for LRU eviction
        km: KnowledgeMemoryManager instance
    """

    def __init__(self, max_size: int = 20):
        """
        Initialize working memory.

        Args:
            max_size: Maximum number of facts to cache (default 20)
        """
        self.logger = logging.getLogger(__name__)
        self.max_size = max_size
        self.cache: OrderedDict[int, KnowledgeFact] = OrderedDict()
        self.km = KnowledgeMemoryManager()

    def add_fact(self, fact: KnowledgeFact) -> None:
        """
        Add a fact to working memory.

        Uses LRU eviction if cache is full. Most recent facts stay in cache.

        Args:
            fact: KnowledgeFact to add to cache
        """
        # Move to end if already in cache (mark as recently used)
        if fact.id in self.cache:
            self.cache.move_to_end(fact.id)
            return

        # Add new fact
        self.cache[fact.id] = fact

        # Evict oldest if over capacity
        if len(self.cache) > self.max_size:
            oldest_id = next(iter(self.cache))
            evicted = self.cache.pop(oldest_id)
            self.logger.debug(f"Evicted fact {evicted.id} from working memory")

    def get_recent_facts(
        self, limit: Optional[int] = None, category: Optional[str] = None
    ) -> List[KnowledgeFact]:
        """
        Get recent facts from working memory.

        Args:
            limit: Maximum number of facts to return (None = all)
            category: Filter by category (None = all categories)

        Returns:
            List of recent facts, most recent first
        """
        facts = list(self.cache.values())

        # Filter by category if specified
        if category:
            facts = [f for f in facts if f.category == category]

        # Reverse to get most recent first
        facts.reverse()

        # Apply limit
        if limit:
            facts = facts[:limit]

        return facts

    def clear(self) -> None:
        """Clear all facts from working memory."""
        self.cache.clear()
        self.logger.info("Working memory cleared")

    def size(self) -> int:
        """Get current number of facts in cache."""
        return len(self.cache)

    def get_important_facts(
        self, threshold: float = 0.8
    ) -> List[KnowledgeFact]:
        """
        Get high-confidence facts from working memory.

        Args:
            threshold: Minimum confidence score (0.0-1.0)

        Returns:
            List of high-confidence facts
        """
        return [
            fact
            for fact in self.cache.values()
            if fact.confidence >= threshold
        ]

    def refresh_from_database(
        self, category: Optional[str] = None, limit: int = 10
    ) -> None:
        """
        Refresh cache from database with recent facts.

        Args:
            category: Category to refresh (None = all)
            limit: Number of facts to load
        """
        self.clear()

        # Get recent facts from database
        facts = self.km.get_all_facts(
            category=category, enabled_only=True, limit=limit
        )

        # Add to cache (most recent first)
        for fact in reversed(facts):
            self.add_fact(fact)

        self.logger.info(f"Refreshed working memory with {len(facts)} facts")

    def get_context_for_prompt(
        self,
        query: Optional[str] = None,
        max_facts: int = 5,
        categories: Optional[List[str]] = None,
    ) -> str:
        """
        Get context string for LLM prompt injection.

        Args:
            query: Optional query to find relevant facts
            max_facts: Maximum number of facts to include
            categories: Filter by categories

        Returns:
            Formatted context string with relevant facts
        """
        if query:
            # Use semantic search if query provided
            facts = self.km.recall_facts(query, k=max_facts)
        else:
            # Get recent facts from cache
            facts = self.get_recent_facts(limit=max_facts)

        # Filter by categories if specified
        if categories:
            facts = [f for f in facts if f.category in categories]

        if not facts:
            return ""

        # Format as context
        context_parts = ["Relevant facts from memory:"]
        for fact in facts:
            verified_mark = "✓" if fact.verified else ""
            context_parts.append(f"- {fact.text} {verified_mark}")

        return "\n".join(context_parts)

    def prune_low_importance_facts(
        self, min_confidence: float = 0.5, min_access_count: int = 1
    ) -> int:
        """
        Remove low-importance facts from working memory.

        Importance is determined by confidence score and access patterns.

        Args:
            min_confidence: Minimum confidence to keep
            min_access_count: Minimum access count to keep (future use)

        Returns:
            Number of facts pruned
        """
        initial_size = len(self.cache)

        # Filter out low confidence facts
        to_remove = [
            fact_id
            for fact_id, fact in self.cache.items()
            if fact.confidence < min_confidence
        ]

        for fact_id in to_remove:
            del self.cache[fact_id]

        pruned_count = initial_size - len(self.cache)

        if pruned_count > 0:
            self.logger.info(f"Pruned {pruned_count} low-importance facts")

        return pruned_count
