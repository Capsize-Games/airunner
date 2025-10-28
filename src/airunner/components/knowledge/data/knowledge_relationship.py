"""
Knowledge relationship model for tracking connections between facts.

Enables relationship graphs, entity linking, and fact verification chains.
"""

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, JSON
from sqlalchemy.sql import func
from airunner.components.data.models.base import BaseModel
from airunner.components.knowledge.enums import (
    KnowledgeRelationshipType,
    EntityType,
)


class KnowledgeRelationship(BaseModel):
    """
    Tracks relationships between knowledge facts and entities.

    Supports fact-to-fact relationships (contradictions, updates),
    entity relationships (person knows person), and verification chains.

    Attributes:
        source_fact_id: ID of the source fact
        target_fact_id: ID of the target fact (None for entity
            relationships)
        relationship_type: Type of relationship (contradicts, updates,
            supports, mentions_entity, etc.)
        entity_name: Name of entity if this is an entity relationship
        entity_type: Type of entity (person, place, organization, etc.)
        confidence: Confidence in this relationship (0.0-1.0)
        metadata_json: Additional metadata as JSON
        created_at: When relationship was created
    """

    __tablename__ = "knowledge_relationships"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Fact relationships
    source_fact_id = Column(Integer, nullable=False, index=True)
    target_fact_id = Column(Integer, nullable=True, index=True)

    # Relationship metadata
    relationship_type = Column(
        String(50), nullable=False, index=True
    )  # contradicts, updates, supports, mentions_entity, etc.

    # Entity information (for entity relationships)
    entity_name = Column(String(200), nullable=True, index=True)
    entity_type = Column(
        String(50), nullable=True, index=True
    )  # person, place, organization, product, concept

    # Confidence and metadata
    confidence = Column(Float, nullable=False, default=0.9)
    metadata_json = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime, nullable=False, default=func.now(), index=True
    )

    @property
    def is_entity_relationship(self) -> bool:
        """Check if this is an entity relationship."""
        return self.entity_name is not None

    @property
    def is_fact_relationship(self) -> bool:
        """Check if this is a fact-to-fact relationship."""
        return self.target_fact_id is not None

    @property
    def metadata_dict(self) -> dict:
        """Get metadata as dictionary."""
        return self.metadata_json if self.metadata_json else {}

    @property
    def relationship_type_enum(self) -> KnowledgeRelationshipType:
        """
        Get relationship type as enum.

        Returns:
            KnowledgeRelationshipType enum value
        """
        try:
            return KnowledgeRelationshipType(self.relationship_type)
        except ValueError:
            return KnowledgeRelationshipType.RELATES_TO

    @property
    def entity_type_enum(self) -> EntityType:
        """
        Get entity type as enum.

        Returns:
            EntityType enum value
        """
        if not self.entity_type:
            return EntityType.CONCEPT
        try:
            return EntityType(self.entity_type)
        except ValueError:
            return EntityType.CONCEPT
