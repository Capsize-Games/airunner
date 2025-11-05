"""Tests for knowledge relationship system."""

import pytest
from airunner.components.knowledge.data.models import KnowledgeFact
from airunner.components.knowledge.data.knowledge_relationship import (
    KnowledgeRelationship,
)
from airunner.components.knowledge.enums import (
    KnowledgeRelationshipType,
    EntityType,
    KnowledgeFactCategory,
)
from airunner.components.knowledge.knowledge_memory_manager import (
    KnowledgeMemoryManager,
)
from airunner.components.data.session_manager import session_scope


@pytest.fixture(autouse=True)
def clean_database():
    """Clean database before and after each test."""
    with session_scope() as session:
        session.query(KnowledgeRelationship).delete()
        session.query(KnowledgeFact).delete()
        session.commit()
    yield
    with session_scope() as session:
        session.query(KnowledgeRelationship).delete()
        session.query(KnowledgeFact).delete()
        session.commit()


class TestKnowledgeRelationshipType:
    """Test KnowledgeRelationshipType enum."""

    def test_relationship_type_values(self):
        """Test that all relationship types exist."""
        assert KnowledgeRelationshipType.CONTRADICTS.value == "contradicts"
        assert KnowledgeRelationshipType.UPDATES.value == "updates"
        assert KnowledgeRelationshipType.SUPPORTS.value == "supports"
        assert KnowledgeRelationshipType.RELATES_TO.value == "relates_to"
        assert (
            KnowledgeRelationshipType.MENTIONS_ENTITY.value
            == "mentions_entity"
        )


class TestEntityType:
    """Test EntityType enum."""

    def test_entity_type_values(self):
        """Test that all entity types exist."""
        assert EntityType.PERSON.value == "person"
        assert EntityType.PLACE.value == "place"
        assert EntityType.ORGANIZATION.value == "organization"
        assert EntityType.PRODUCT.value == "product"
        assert EntityType.CONCEPT.value == "concept"
        assert EntityType.EVENT.value == "event"
        assert EntityType.DATE.value == "date"


class TestKnowledgeRelationshipModel:
    """Test KnowledgeRelationship model."""

    def setup_method(self):
        """Create test facts for relationships."""
        self.km = KnowledgeMemoryManager()

        # Create test facts
        self.fact1 = self.km.add_fact(
            text="John works at Google",
            category=KnowledgeFactCategory.USER_WORK.value,
        )
        self.fact2 = self.km.add_fact(
            text="John is a software engineer",
            category=KnowledgeFactCategory.USER_WORK.value,
        )

    def test_create_entity_relationship(self):
        """Test creating an entity relationship."""
        with session_scope() as session:
            rel = KnowledgeRelationship(
                source_fact_id=self.fact1.id,
                relationship_type=KnowledgeRelationshipType.MENTIONS_ENTITY.value,
                entity_name="John",
                entity_type=EntityType.PERSON.value,
                confidence=0.95,
            )
            session.add(rel)
            session.commit()

            # Query back
            result = (
                session.query(KnowledgeRelationship)
                .filter_by(source_fact_id=self.fact1.id)
                .first()
            )

            assert result is not None
            assert result.entity_name == "John"
            assert result.entity_type == EntityType.PERSON.value
            assert result.is_entity_relationship is True
            assert result.is_fact_relationship is False

    def test_create_fact_relationship(self):
        """Test creating a fact-to-fact relationship."""
        with session_scope() as session:
            rel = KnowledgeRelationship(
                source_fact_id=self.fact1.id,
                target_fact_id=self.fact2.id,
                relationship_type=KnowledgeRelationshipType.SUPPORTS.value,
                confidence=0.9,
            )
            session.add(rel)
            session.commit()

            # Query back
            result = (
                session.query(KnowledgeRelationship)
                .filter_by(
                    source_fact_id=self.fact1.id,
                    target_fact_id=self.fact2.id,
                )
                .first()
            )

            assert result is not None
            assert result.is_fact_relationship is True
            assert result.is_entity_relationship is False
            assert (
                result.relationship_type
                == KnowledgeRelationshipType.SUPPORTS.value
            )

    def test_relationship_type_enum_property(self):
        """Test relationship_type_enum property."""
        with session_scope() as session:
            rel = KnowledgeRelationship(
                source_fact_id=self.fact1.id,
                relationship_type=KnowledgeRelationshipType.CONTRADICTS.value,
                entity_name="Test",
                entity_type=EntityType.CONCEPT.value,
            )
            session.add(rel)
            session.commit()
            session.refresh(rel)

            assert (
                rel.relationship_type_enum
                == KnowledgeRelationshipType.CONTRADICTS
            )

    def test_entity_type_enum_property(self):
        """Test entity_type_enum property."""
        with session_scope() as session:
            rel = KnowledgeRelationship(
                source_fact_id=self.fact1.id,
                relationship_type=KnowledgeRelationshipType.MENTIONS_ENTITY.value,
                entity_name="Google",
                entity_type=EntityType.ORGANIZATION.value,
            )
            session.add(rel)
            session.commit()
            session.refresh(rel)

            assert rel.entity_type_enum == EntityType.ORGANIZATION


class TestKnowledgeMemoryManagerRelationships:
    """Test KnowledgeMemoryManager relationship methods."""

    def setup_method(self):
        """Create test data."""
        self.km = KnowledgeMemoryManager()

        # Create test facts
        self.fact1 = self.km.add_fact(
            text="John works at Google as a software engineer",
            category=KnowledgeFactCategory.USER_WORK.value,
        )
        self.fact2 = self.km.add_fact(
            text="John lives in New York",
            category=KnowledgeFactCategory.USER_LOCATION.value,
        )
        self.fact3 = self.km.add_fact(
            text="John enjoys hiking",
            category=KnowledgeFactCategory.USER_INTERESTS.value,
        )

        # Create entity relationships
        with session_scope() as session:
            # John is a person
            session.add(
                KnowledgeRelationship(
                    source_fact_id=self.fact1.id,
                    relationship_type=KnowledgeRelationshipType.MENTIONS_ENTITY.value,
                    entity_name="John",
                    entity_type=EntityType.PERSON.value,
                )
            )
            session.add(
                KnowledgeRelationship(
                    source_fact_id=self.fact2.id,
                    relationship_type=KnowledgeRelationshipType.MENTIONS_ENTITY.value,
                    entity_name="John",
                    entity_type=EntityType.PERSON.value,
                )
            )
            session.add(
                KnowledgeRelationship(
                    source_fact_id=self.fact3.id,
                    relationship_type=KnowledgeRelationshipType.MENTIONS_ENTITY.value,
                    entity_name="John",
                    entity_type=EntityType.PERSON.value,
                )
            )

            # Google is an organization
            session.add(
                KnowledgeRelationship(
                    source_fact_id=self.fact1.id,
                    relationship_type=KnowledgeRelationshipType.MENTIONS_ENTITY.value,
                    entity_name="Google",
                    entity_type=EntityType.ORGANIZATION.value,
                )
            )

            # New York is a place
            session.add(
                KnowledgeRelationship(
                    source_fact_id=self.fact2.id,
                    relationship_type=KnowledgeRelationshipType.MENTIONS_ENTITY.value,
                    entity_name="New York",
                    entity_type=EntityType.PLACE.value,
                )
            )

            session.commit()

    def test_get_fact_entities(self):
        """Test retrieving entities from a fact."""
        entities = self.km.get_fact_entities(self.fact1.id)

        assert len(entities) == 2
        entity_names = [e["name"] for e in entities]
        assert "John" in entity_names
        assert "Google" in entity_names

        # Check entity types
        for entity in entities:
            if entity["name"] == "John":
                assert entity["type"] == EntityType.PERSON.value
            elif entity["name"] == "Google":
                assert entity["type"] == EntityType.ORGANIZATION.value

    def test_get_facts_by_entity(self):
        """Test finding all facts mentioning an entity."""
        facts = self.km.get_facts_by_entity("John")

        assert len(facts) == 3
        fact_ids = [f.id for f in facts]
        assert self.fact1.id in fact_ids
        assert self.fact2.id in fact_ids
        assert self.fact3.id in fact_ids

    def test_get_facts_by_entity_with_type_filter(self):
        """Test finding facts by entity with type filter."""
        facts = self.km.get_facts_by_entity("John", EntityType.PERSON.value)

        assert len(facts) == 3

        # Should return empty for wrong type
        facts = self.km.get_facts_by_entity(
            "John", EntityType.ORGANIZATION.value
        )
        assert len(facts) == 0

    def test_add_fact_relationship(self):
        """Test creating a fact-to-fact relationship."""
        success = self.km.add_fact_relationship(
            source_fact_id=self.fact1.id,
            target_fact_id=self.fact2.id,
            relationship_type=KnowledgeRelationshipType.SUPPORTS.value,
            confidence=0.85,
        )

        assert success is True

        # Verify relationship exists
        with session_scope() as session:
            rel = (
                session.query(KnowledgeRelationship)
                .filter_by(
                    source_fact_id=self.fact1.id,
                    target_fact_id=self.fact2.id,
                )
                .first()
            )

            assert rel is not None
            assert (
                rel.relationship_type
                == KnowledgeRelationshipType.SUPPORTS.value
            )
            assert rel.confidence == 0.85

    def test_add_duplicate_fact_relationship(self):
        """Test that duplicate relationships are not created."""
        # Create first relationship
        success1 = self.km.add_fact_relationship(
            source_fact_id=self.fact1.id,
            target_fact_id=self.fact2.id,
            relationship_type=KnowledgeRelationshipType.SUPPORTS.value,
        )
        assert success1 is True

        # Try to create duplicate
        success2 = self.km.add_fact_relationship(
            source_fact_id=self.fact1.id,
            target_fact_id=self.fact2.id,
            relationship_type=KnowledgeRelationshipType.SUPPORTS.value,
        )
        assert success2 is False

    def test_get_related_facts(self):
        """Test retrieving related facts."""
        # Create relationships
        self.km.add_fact_relationship(
            source_fact_id=self.fact1.id,
            target_fact_id=self.fact2.id,
            relationship_type=KnowledgeRelationshipType.SUPPORTS.value,
        )
        self.km.add_fact_relationship(
            source_fact_id=self.fact1.id,
            target_fact_id=self.fact3.id,
            relationship_type=KnowledgeRelationshipType.RELATES_TO.value,
        )

        # Get related facts
        related = self.km.get_related_facts(self.fact1.id)

        assert len(related) == 2
        fact_ids = [r["fact"].id for r in related]
        assert self.fact2.id in fact_ids
        assert self.fact3.id in fact_ids

    def test_get_related_facts_with_type_filter(self):
        """Test retrieving related facts with relationship type filter."""
        # Create relationships
        self.km.add_fact_relationship(
            source_fact_id=self.fact1.id,
            target_fact_id=self.fact2.id,
            relationship_type=KnowledgeRelationshipType.SUPPORTS.value,
        )
        self.km.add_fact_relationship(
            source_fact_id=self.fact1.id,
            target_fact_id=self.fact3.id,
            relationship_type=KnowledgeRelationshipType.CONTRADICTS.value,
        )

        # Filter for SUPPORTS only
        related = self.km.get_related_facts(
            self.fact1.id,
            relationship_types=[KnowledgeRelationshipType.SUPPORTS.value],
        )

        assert len(related) == 1
        assert related[0]["fact"].id == self.fact2.id
        assert (
            related[0]["relationship_type"]
            == KnowledgeRelationshipType.SUPPORTS.value
        )
