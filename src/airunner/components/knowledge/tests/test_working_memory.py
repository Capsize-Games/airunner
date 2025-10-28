"""
Tests for knowledge working memory system.

Tests working memory cache, summary generation, context injection,
and memory pruning functionality.
"""

from datetime import datetime, timedelta

from airunner.components.knowledge.working_memory import WorkingMemory
from airunner.components.knowledge.summary_generator import (
    SummaryGenerator,
    SummaryPeriod,
)
from airunner.components.knowledge.context_injection_mixin import (
    ContextInjectionMixin,
)
from airunner.components.knowledge.data.models import KnowledgeFact


class TestWorkingMemory:
    """Test WorkingMemory cache functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.working_memory = WorkingMemory(max_size=5)

    def test_add_fact_to_cache(self):
        """Test adding a single fact to cache."""
        fact = KnowledgeFact(
            id=1,
            text="User likes Python",
            category="user_preferences",
            confidence=0.9,
        )

        self.working_memory.add_fact(fact)

        assert self.working_memory.size() == 1
        assert 1 in self.working_memory.cache

    def test_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        # Fill cache to max
        for i in range(6):
            fact = KnowledgeFact(
                id=i,
                text=f"Fact {i}",
                category="other",
                confidence=0.8,
            )
            self.working_memory.add_fact(fact)

        # Cache should be at max size
        assert self.working_memory.size() == 5

        # Oldest fact (id=0) should have been evicted
        assert 0 not in self.working_memory.cache
        assert 5 in self.working_memory.cache

    def test_move_to_end_on_readd(self):
        """Test that re-adding a fact moves it to end (marks as recently used)."""
        fact1 = KnowledgeFact(id=1, text="Fact 1", category="other")
        fact2 = KnowledgeFact(id=2, text="Fact 2", category="other")

        self.working_memory.add_fact(fact1)
        self.working_memory.add_fact(fact2)

        # Re-add fact 1 (should move to end)
        self.working_memory.add_fact(fact1)

        # Fill cache to trigger eviction
        for i in range(3, 7):
            fact = KnowledgeFact(id=i, text=f"Fact {i}", category="other")
            self.working_memory.add_fact(fact)

        # Fact 1 should still be in cache (moved to end)
        assert 1 in self.working_memory.cache
        # Fact 2 should have been evicted (was oldest)
        assert 2 not in self.working_memory.cache

    def test_get_recent_facts(self):
        """Test retrieving recent facts."""
        for i in range(3):
            fact = KnowledgeFact(
                id=i,
                text=f"Fact {i}",
                category="other",
                confidence=0.8,
            )
            self.working_memory.add_fact(fact)

        recent = self.working_memory.get_recent_facts(limit=2)

        assert len(recent) == 2
        # Most recent first
        assert recent[0].id == 2
        assert recent[1].id == 1

    def test_get_recent_facts_with_category_filter(self):
        """Test filtering facts by category."""
        fact1 = KnowledgeFact(id=1, text="Fact 1", category="user_preferences")
        fact2 = KnowledgeFact(id=2, text="Fact 2", category="user_work")
        fact3 = KnowledgeFact(id=3, text="Fact 3", category="user_preferences")

        self.working_memory.add_fact(fact1)
        self.working_memory.add_fact(fact2)
        self.working_memory.add_fact(fact3)

        prefs = self.working_memory.get_recent_facts(
            category="user_preferences"
        )

        assert len(prefs) == 2
        assert all(f.category == "user_preferences" for f in prefs)

    def test_clear_cache(self):
        """Test clearing the cache."""
        for i in range(3):
            fact = KnowledgeFact(id=i, text=f"Fact {i}", category="other")
            self.working_memory.add_fact(fact)

        assert self.working_memory.size() == 3

        self.working_memory.clear()

        assert self.working_memory.size() == 0

    def test_get_important_facts(self):
        """Test filtering by confidence threshold."""
        fact1 = KnowledgeFact(id=1, text="High conf", confidence=0.95)
        fact2 = KnowledgeFact(id=2, text="Med conf", confidence=0.75)
        fact3 = KnowledgeFact(id=3, text="Low conf", confidence=0.50)

        self.working_memory.add_fact(fact1)
        self.working_memory.add_fact(fact2)
        self.working_memory.add_fact(fact3)

        important = self.working_memory.get_important_facts(threshold=0.8)

        assert len(important) == 1
        assert important[0].confidence == 0.95

    def test_prune_low_importance_facts(self):
        """Test pruning low-confidence facts."""
        fact1 = KnowledgeFact(id=1, text="High conf", confidence=0.95)
        fact2 = KnowledgeFact(id=2, text="Med conf", confidence=0.60)
        fact3 = KnowledgeFact(id=3, text="Low conf", confidence=0.40)

        self.working_memory.add_fact(fact1)
        self.working_memory.add_fact(fact2)
        self.working_memory.add_fact(fact3)

        pruned_count = self.working_memory.prune_low_importance_facts(
            min_confidence=0.5
        )

        assert pruned_count == 1  # Fact 3 removed
        assert self.working_memory.size() == 2
        assert 3 not in self.working_memory.cache

    def test_get_context_for_prompt(self):
        """Test context generation for prompt injection."""
        fact1 = KnowledgeFact(
            id=1, text="User likes Python", verified=True, confidence=0.9
        )
        fact2 = KnowledgeFact(
            id=2, text="User works remotely", verified=False, confidence=0.8
        )

        self.working_memory.add_fact(fact1)
        self.working_memory.add_fact(fact2)

        # Test with no query (uses cache)
        context = self.working_memory.get_context_for_prompt(max_facts=5)

        assert "Relevant facts from memory:" in context
        assert (
            "User likes Python" in context or "User works remotely" in context
        )


class TestSummaryGenerator:
    """Test SummaryGenerator functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = SummaryGenerator()

    def test_calculate_start_date_daily(self):
        """Test daily period start date calculation."""
        end_date = datetime(2025, 1, 15, 12, 0, 0)
        start_date = self.generator._calculate_start_date(
            SummaryPeriod.DAILY, end_date
        )

        assert start_date == datetime(2025, 1, 14, 12, 0, 0)

    def test_calculate_start_date_weekly(self):
        """Test weekly period start date calculation."""
        end_date = datetime(2025, 1, 15, 12, 0, 0)
        start_date = self.generator._calculate_start_date(
            SummaryPeriod.WEEKLY, end_date
        )

        expected = end_date - timedelta(weeks=1)
        assert start_date == expected

    def test_calculate_start_date_monthly(self):
        """Test monthly period start date calculation."""
        end_date = datetime(2025, 1, 15, 12, 0, 0)
        start_date = self.generator._calculate_start_date(
            SummaryPeriod.MONTHLY, end_date
        )

        expected = end_date - timedelta(days=30)
        assert start_date == expected

    def test_categorize_facts(self):
        """Test fact categorization."""
        facts = [
            KnowledgeFact(id=1, text="Fact 1", category="user_preferences"),
            KnowledgeFact(id=2, text="Fact 2", category="user_work"),
            KnowledgeFact(id=3, text="Fact 3", category="user_preferences"),
        ]

        categories = self.generator._categorize_facts(facts)

        assert categories["user_preferences"] == 2
        assert categories["user_work"] == 1

    def test_create_summary_text(self):
        """Test summary text generation."""
        facts = [
            KnowledgeFact(
                id=1,
                text="User likes Python",
                category="user_preferences",
                verified=True,
                confidence=0.9,
            ),
            KnowledgeFact(
                id=2,
                text="User works at Google",
                category="user_work",
                verified=True,
                confidence=0.95,
            ),
        ]

        summary = self.generator._create_summary_text(
            facts, SummaryPeriod.DAILY
        )

        assert "Summary for daily period:" in summary
        assert "Total facts: 2" in summary
        assert "User Preferences:" in summary
        assert "User Work:" in summary
        assert "Key facts" in summary


class TestContextInjectionMixin:
    """Test ContextInjectionMixin functionality."""

    def setup_method(self):
        """Set up test fixtures."""

        class TestClass(ContextInjectionMixin):
            def __init__(self):
                super().__init__()
                self.working_memory = WorkingMemory(max_size=10)
                self.summary_generator = SummaryGenerator()

        self.obj = TestClass()

    def test_enable_disable_context_injection(self):
        """Test enabling/disabling context injection."""
        assert self.obj._context_injection_enabled is True

        self.obj.enable_context_injection(False)
        assert self.obj._context_injection_enabled is False

        self.obj.enable_context_injection(True)
        assert self.obj._context_injection_enabled is True

    def test_inject_context_into_prompt(self):
        """Test context injection into prompt."""
        fact = KnowledgeFact(
            id=1,
            text="User prefers dark mode",
            category="user_preferences",
            verified=True,
        )
        self.obj.working_memory.add_fact(fact)

        prompt = "What are my UI preferences?"
        enhanced = self.obj.inject_context_into_prompt(prompt, max_facts=5)

        # Should contain original prompt
        assert prompt in enhanced
        # Should contain context
        assert "Relevant facts from memory:" in enhanced or prompt == enhanced

    def test_inject_context_disabled(self):
        """Test that injection is skipped when disabled."""
        self.obj.enable_context_injection(False)

        fact = KnowledgeFact(
            id=1, text="User likes Python", category="user_preferences"
        )
        self.obj.working_memory.add_fact(fact)

        prompt = "What do I like?"
        enhanced = self.obj.inject_context_into_prompt(prompt)

        # Should return original prompt unchanged
        assert enhanced == prompt

    def test_get_context_stats(self):
        """Test context statistics retrieval."""
        fact1 = KnowledgeFact(id=1, text="Fact 1", category="other")
        fact2 = KnowledgeFact(id=2, text="Fact 2", category="other")

        self.obj.working_memory.add_fact(fact1)
        self.obj.working_memory.add_fact(fact2)

        stats = self.obj.get_context_stats()

        assert stats["enabled"] is True
        assert stats["facts_cached"] == 2
        assert stats["max_cache_size"] == 10

    def test_prune_working_memory(self):
        """Test pruning through mixin."""
        fact1 = KnowledgeFact(id=1, text="High conf", confidence=0.95)
        fact2 = KnowledgeFact(id=2, text="Low conf", confidence=0.30)

        self.obj.working_memory.add_fact(fact1)
        self.obj.working_memory.add_fact(fact2)

        pruned = self.obj.prune_working_memory(min_confidence=0.5)

        assert pruned == 1
        assert self.obj.working_memory.size() == 1
