"""Tests for knowledge fact categories."""

import pytest

from airunner.components.knowledge.enums import (
    KnowledgeFactCategory,
    KnowledgeSource,
)
from airunner.components.knowledge.data.models import KnowledgeFact
from airunner.components.knowledge.knowledge_memory_manager import (
    KnowledgeMemoryManager,
)
from airunner.components.data.session_manager import session_scope


@pytest.fixture(autouse=True)
def clean_database():
    """Clean knowledge facts before and after each test."""
    # Clean before test
    with session_scope() as session:
        session.query(KnowledgeFact).delete()
        session.commit()

    yield

    # Clean after test
    with session_scope() as session:
        session.query(KnowledgeFact).delete()
        session.commit()


class TestKnowledgeFactCategory:
    """Test KnowledgeFactCategory enum."""

    def test_category_values(self):
        """Test category enum values."""
        assert KnowledgeFactCategory.USER_IDENTITY.value == "user_identity"
        assert KnowledgeFactCategory.WORLD_KNOWLEDGE.value == "world_knowledge"
        assert KnowledgeFactCategory.TEMPORAL_EVENT.value == "temporal_event"
        assert KnowledgeFactCategory.ENTITY_PERSON.value == "entity_person"
        assert KnowledgeFactCategory.RELATIONSHIP.value == "relationship"

    def test_legacy_category_mapping(self):
        """Test conversion from legacy categories."""
        assert (
            KnowledgeFactCategory.from_legacy_category("identity")
            == KnowledgeFactCategory.USER_IDENTITY
        )
        assert (
            KnowledgeFactCategory.from_legacy_category("location")
            == KnowledgeFactCategory.USER_LOCATION
        )
        assert (
            KnowledgeFactCategory.from_legacy_category("health")
            == KnowledgeFactCategory.USER_HEALTH
        )
        assert (
            KnowledgeFactCategory.from_legacy_category("unknown")
            == KnowledgeFactCategory.OTHER
        )

    def test_to_legacy_category(self):
        """Test conversion to legacy categories."""
        assert (
            KnowledgeFactCategory.to_legacy_category(
                KnowledgeFactCategory.USER_IDENTITY
            )
            == "identity"
        )
        assert (
            KnowledgeFactCategory.to_legacy_category(
                KnowledgeFactCategory.USER_HEALTH
            )
            == "health"
        )
        assert (
            KnowledgeFactCategory.to_legacy_category(
                KnowledgeFactCategory.WORLD_KNOWLEDGE
            )
            == "other"  # No legacy equivalent
        )

    def test_category_type_checks(self):
        """Test category type check properties."""
        # User categories
        assert KnowledgeFactCategory.USER_IDENTITY.is_user_category
        assert KnowledgeFactCategory.USER_HEALTH.is_user_category
        assert not KnowledgeFactCategory.WORLD_KNOWLEDGE.is_user_category

        # World categories
        assert KnowledgeFactCategory.WORLD_KNOWLEDGE.is_world_category
        assert KnowledgeFactCategory.WORLD_SCIENCE.is_world_category
        assert not KnowledgeFactCategory.USER_IDENTITY.is_world_category

        # Temporal categories
        assert KnowledgeFactCategory.TEMPORAL_EVENT.is_temporal_category
        assert KnowledgeFactCategory.TEMPORAL_REMINDER.is_temporal_category
        assert not KnowledgeFactCategory.USER_IDENTITY.is_temporal_category

        # Entity categories
        assert KnowledgeFactCategory.ENTITY_PERSON.is_entity_category
        assert KnowledgeFactCategory.ENTITY_PLACE.is_entity_category
        assert not KnowledgeFactCategory.USER_IDENTITY.is_entity_category

        # Relationship category
        assert KnowledgeFactCategory.RELATIONSHIP.is_relationship_category
        assert not KnowledgeFactCategory.USER_IDENTITY.is_relationship_category


class TestKnowledgeFactModel:
    """Test KnowledgeFact model with categories."""

    def test_fact_category_enum_property(self):
        """Test category_enum property."""
        with session_scope() as session:
            # Test with enum value
            fact1 = KnowledgeFact(
                text="Test fact",
                category=KnowledgeFactCategory.USER_IDENTITY.value,
            )
            session.add(fact1)
            session.commit()

            assert fact1.category_enum == KnowledgeFactCategory.USER_IDENTITY
            assert fact1.is_user_fact

    def test_fact_legacy_category_conversion(self):
        """Test legacy category conversion."""
        with session_scope() as session:
            # Test with legacy category
            fact = KnowledgeFact(
                text="User is 30 years old",
                category="identity",  # Legacy category
            )
            session.add(fact)
            session.commit()

            assert fact.category_enum == KnowledgeFactCategory.USER_IDENTITY
            assert fact.is_user_fact

    def test_fact_type_properties(self):
        """Test fact type check properties."""
        with session_scope() as session:
            # User fact
            user_fact = KnowledgeFact(
                text="User lives in Seattle",
                category=KnowledgeFactCategory.USER_LOCATION.value,
            )
            session.add(user_fact)

            # World fact
            world_fact = KnowledgeFact(
                text="Python is a programming language",
                category=KnowledgeFactCategory.WORLD_KNOWLEDGE.value,
            )
            session.add(world_fact)

            # Temporal fact
            temporal_fact = KnowledgeFact(
                text="Meeting at 3pm",
                category=KnowledgeFactCategory.TEMPORAL_EVENT.value,
            )
            session.add(temporal_fact)

            # Entity fact
            entity_fact = KnowledgeFact(
                text="John works at Acme Corp",
                category=KnowledgeFactCategory.ENTITY_PERSON.value,
            )
            session.add(entity_fact)

            session.commit()

            assert user_fact.is_user_fact
            assert not user_fact.is_world_fact

            assert world_fact.is_world_fact
            assert not world_fact.is_user_fact

            assert temporal_fact.is_temporal_fact
            assert not temporal_fact.is_entity_fact

            assert entity_fact.is_entity_fact
            assert not entity_fact.is_temporal_fact

    def test_fact_source_enum_property(self):
        """Test source_enum property."""
        with session_scope() as session:
            fact = KnowledgeFact(
                text="Test fact",
                category="other",
                source=KnowledgeSource.DOCUMENT.value,
            )
            session.add(fact)
            session.commit()

            assert fact.source_enum == KnowledgeSource.DOCUMENT


class TestKnowledgeMemoryManagerCategories:
    """Test KnowledgeMemoryManager category filtering."""

    def setup_method(self):
        """Set up test data."""
        self.manager = KnowledgeMemoryManager()

        with session_scope() as session:
            # Add user facts
            session.add(
                KnowledgeFact(
                    text="User is 30 years old",
                    category=KnowledgeFactCategory.USER_IDENTITY.value,
                )
            )
            session.add(
                KnowledgeFact(
                    text="User lives in New York",
                    category=KnowledgeFactCategory.USER_LOCATION.value,
                )
            )
            session.add(
                KnowledgeFact(
                    text="User likes pizza",
                    category=KnowledgeFactCategory.USER_PREFERENCES.value,
                )
            )

            # Add world facts
            session.add(
                KnowledgeFact(
                    text="Python was created in 1991",
                    category=KnowledgeFactCategory.WORLD_HISTORY.value,
                )
            )
            session.add(
                KnowledgeFact(
                    text="Water boils at 100°C",
                    category=KnowledgeFactCategory.WORLD_SCIENCE.value,
                )
            )

            # Add temporal facts
            session.add(
                KnowledgeFact(
                    text="Meeting tomorrow at 3pm",
                    category=KnowledgeFactCategory.TEMPORAL_EVENT.value,
                )
            )
            session.add(
                KnowledgeFact(
                    text="Project deadline next Friday",
                    category=KnowledgeFactCategory.TEMPORAL_DEADLINE.value,
                )
            )

            # Add entity facts
            session.add(
                KnowledgeFact(
                    text="John Smith is the CEO",
                    category=KnowledgeFactCategory.ENTITY_PERSON.value,
                )
            )
            session.add(
                KnowledgeFact(
                    text="Seattle is in Washington",
                    category=KnowledgeFactCategory.ENTITY_PLACE.value,
                )
            )

            session.commit()

    def test_filter_by_single_category(self):
        """Test filtering by single category."""
        facts = self.manager.get_all_facts(
            category=KnowledgeFactCategory.USER_IDENTITY.value
        )

        assert len(facts) == 1
        assert facts[0].text == "User is 30 years old"

    def test_filter_by_multiple_categories(self):
        """Test filtering by multiple categories."""
        facts = self.manager.get_all_facts(
            category=[
                KnowledgeFactCategory.USER_IDENTITY.value,
                KnowledgeFactCategory.USER_LOCATION.value,
            ]
        )

        assert len(facts) == 2
        texts = [f.text for f in facts]
        assert "User is 30 years old" in texts
        assert "User lives in New York" in texts

    def test_filter_by_category_type_user(self):
        """Test filtering by user category type."""
        facts = self.manager.get_facts_by_category_type(is_user=True)

        assert len(facts) == 3
        for fact in facts:
            assert fact.is_user_fact

    def test_filter_by_category_type_world(self):
        """Test filtering by world category type."""
        facts = self.manager.get_facts_by_category_type(is_world=True)

        assert len(facts) == 2
        for fact in facts:
            assert fact.is_world_fact

    def test_filter_by_category_type_temporal(self):
        """Test filtering by temporal category type."""
        facts = self.manager.get_facts_by_category_type(is_temporal=True)

        assert len(facts) == 2
        for fact in facts:
            assert fact.is_temporal_fact

    def test_filter_by_category_type_entity(self):
        """Test filtering by entity category type."""
        facts = self.manager.get_facts_by_category_type(is_entity=True)

        assert len(facts) == 2
        for fact in facts:
            assert fact.is_entity_fact

    def test_filter_by_multiple_category_types(self):
        """Test filtering by multiple category types."""
        facts = self.manager.get_facts_by_category_type(
            is_user=True, is_world=True
        )

        assert len(facts) == 5  # 3 user + 2 world

    def test_filter_by_source(self):
        """Test filtering by source."""
        # Add facts with different sources
        with session_scope() as session:
            session.add(
                KnowledgeFact(
                    text="Fact from document",
                    category="other",
                    source=KnowledgeSource.DOCUMENT.value,
                )
            )
            session.add(
                KnowledgeFact(
                    text="Fact from web",
                    category="other",
                    source=KnowledgeSource.WEB.value,
                )
            )
            session.commit()

        # Filter by single source
        facts = self.manager.get_all_facts(
            source=KnowledgeSource.DOCUMENT.value
        )
        assert len(facts) == 1
        assert facts[0].text == "Fact from document"

        # Filter by multiple sources
        facts = self.manager.get_all_facts(
            source=[KnowledgeSource.DOCUMENT.value, KnowledgeSource.WEB.value]
        )
        assert len(facts) == 2


class TestCategoryMigration:
    """Test category migration scenarios."""

    def test_add_fact_with_new_category(self):
        """Test adding fact with new category system."""
        manager = KnowledgeMemoryManager()

        fact = manager.add_fact(
            text="Paris is the capital of France",
            category=KnowledgeFactCategory.WORLD_GEOGRAPHY.value,
            tags=["geography", "capital", "france"],
            confidence=1.0,
            source=KnowledgeSource.DOCUMENT.value,
        )

        assert fact.category == KnowledgeFactCategory.WORLD_GEOGRAPHY.value
        assert fact.category_enum == KnowledgeFactCategory.WORLD_GEOGRAPHY
        assert fact.is_world_fact
        assert fact.source_enum == KnowledgeSource.DOCUMENT

    def test_legacy_category_still_works(self):
        """Test that legacy categories still work."""
        manager = KnowledgeMemoryManager()

        fact = manager.add_fact(
            text="User is 25 years old",
            category="identity",  # Legacy category
            confidence=0.9,
        )

        assert fact.category == "identity"
        assert fact.category_enum == KnowledgeFactCategory.USER_IDENTITY
        assert fact.is_user_fact
