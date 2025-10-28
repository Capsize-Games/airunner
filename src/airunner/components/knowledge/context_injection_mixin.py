"""
Context injection mixin for integrating working memory with LLM.

Automatically injects relevant facts from working memory into LLM prompts
to provide context and improve response quality.
"""

import logging
from typing import Optional, List

from airunner.components.knowledge.working_memory import WorkingMemory
from airunner.components.knowledge.summary_generator import (
    SummaryGenerator,
    SummaryPeriod,
)


class ContextInjectionMixin:
    """
    Mixin for injecting knowledge context into LLM requests.

    Provides methods to automatically enhance prompts with relevant
    facts from working memory and periodic summaries.

    Usage:
        class MyLLMClass(ContextInjectionMixin, OtherBase):
            def __init__(self):
                super().__init__()
                self.working_memory = WorkingMemory()
                self.summary_generator = SummaryGenerator()
    """

    def __init__(self):
        """Initialize context injection components."""
        self.logger = logging.getLogger(__name__)
        self.working_memory: Optional[WorkingMemory] = None
        self.summary_generator: Optional[SummaryGenerator] = None
        self._context_injection_enabled = True

    def enable_context_injection(self, enabled: bool = True) -> None:
        """
        Enable or disable automatic context injection.

        Args:
            enabled: True to enable, False to disable
        """
        self._context_injection_enabled = enabled
        self.logger.info(
            f"Context injection {'enabled' if enabled else 'disabled'}"
        )

    def inject_context_into_prompt(
        self,
        prompt: str,
        query: Optional[str] = None,
        max_facts: int = 5,
        categories: Optional[List[str]] = None,
        include_summaries: bool = False,
    ) -> str:
        """
        Inject relevant context from working memory into a prompt.

        Args:
            prompt: Original user prompt
            query: Optional query for semantic search (defaults to prompt)
            max_facts: Maximum facts to inject
            categories: Filter by categories
            include_summaries: Whether to include recent summaries

        Returns:
            Enhanced prompt with injected context
        """
        if not self._context_injection_enabled:
            return prompt

        if not self.working_memory:
            self.logger.warning(
                "Working memory not initialized, skipping context injection"
            )
            return prompt

        # Use prompt as query if not specified
        search_query = query or prompt

        # Get relevant context
        context = self.working_memory.get_context_for_prompt(
            query=search_query, max_facts=max_facts, categories=categories
        )

        if not context and not include_summaries:
            return prompt

        # Build enhanced prompt
        enhanced_parts = []

        # Add context from facts
        if context:
            enhanced_parts.append(context)
            enhanced_parts.append("")  # Blank line

        # Add recent summaries if requested
        if include_summaries and self.summary_generator:
            summary_context = self._get_summary_context()
            if summary_context:
                enhanced_parts.append(summary_context)
                enhanced_parts.append("")  # Blank line

        # Add original prompt
        enhanced_parts.append(prompt)

        enhanced_prompt = "\n".join(enhanced_parts)

        self.logger.debug(
            f"Injected context ({len(context.split(chr(10))) if context else 0} lines)"
        )

        return enhanced_prompt

    def _get_summary_context(self) -> str:
        """
        Get context from recent conversation summaries.

        Returns:
            Formatted summary context string
        """
        if not self.summary_generator:
            return ""

        # Get most recent daily summary
        summaries = self.summary_generator.get_recent_summaries(
            period=SummaryPeriod.DAILY, limit=1
        )

        if not summaries:
            return ""

        summary = summaries[0]

        return f"Recent activity summary:\n{summary.summary}"

    def get_context_stats(self) -> dict:
        """
        Get statistics about current working memory context.

        Returns:
            Dict with context statistics
        """
        if not self.working_memory:
            return {"enabled": False, "facts_cached": 0}

        return {
            "enabled": self._context_injection_enabled,
            "facts_cached": self.working_memory.size(),
            "max_cache_size": self.working_memory.max_size,
        }

    def refresh_working_memory(
        self, category: Optional[str] = None, limit: int = 10
    ) -> None:
        """
        Refresh working memory from database.

        Args:
            category: Optional category filter
            limit: Number of facts to load
        """
        if not self.working_memory:
            self.logger.warning("Working memory not initialized")
            return

        self.working_memory.refresh_from_database(
            category=category, limit=limit
        )

        self.logger.info(
            f"Refreshed working memory: {self.working_memory.size()} facts"
        )

    def prune_working_memory(self, min_confidence: float = 0.5) -> int:
        """
        Prune low-importance facts from working memory.

        Args:
            min_confidence: Minimum confidence to keep

        Returns:
            Number of facts pruned
        """
        if not self.working_memory:
            self.logger.warning("Working memory not initialized")
            return 0

        pruned = self.working_memory.prune_low_importance_facts(
            min_confidence=min_confidence
        )

        if pruned > 0:
            self.logger.info(f"Pruned {pruned} facts from working memory")

        return pruned
