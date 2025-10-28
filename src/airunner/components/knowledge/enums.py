"""Enumerations for the knowledge system."""

from enum import Enum


class KnowledgeFactCategory(Enum):
    """
    Categories for organizing knowledge facts.

    Hierarchical organization:
    - USER_*: Facts about the user
    - WORLD_*: General world knowledge
    - TEMPORAL_*: Time-bound information
    - ENTITY_*: Information about specific entities
    """

    # User-specific categories
    USER_IDENTITY = "user_identity"  # Name, age, gender, etc.
    USER_LOCATION = "user_location"  # Where user lives, works
    USER_PREFERENCES = "user_preferences"  # Likes, dislikes, habits
    USER_RELATIONSHIPS = "user_relationships"  # Family, friends
    USER_WORK = "user_work"  # Job, company, projects
    USER_INTERESTS = "user_interests"  # Hobbies, topics of interest
    USER_SKILLS = "user_skills"  # What user can do
    USER_GOALS = "user_goals"  # What user wants to achieve
    USER_HISTORY = "user_history"  # Past events, experiences
    USER_HEALTH = "user_health"  # Medical conditions, symptoms

    # World knowledge categories
    WORLD_KNOWLEDGE = "world_knowledge"  # General facts about the world
    WORLD_SCIENCE = "world_science"  # Scientific facts
    WORLD_HISTORY = "world_history"  # Historical events
    WORLD_GEOGRAPHY = "world_geography"  # Geographic information
    WORLD_CULTURE = "world_culture"  # Cultural knowledge

    # Temporal categories
    TEMPORAL_EVENT = "temporal_event"  # Specific events with timestamps
    TEMPORAL_SCHEDULE = "temporal_schedule"  # Scheduled activities
    TEMPORAL_REMINDER = "temporal_reminder"  # Reminders
    TEMPORAL_DEADLINE = "temporal_deadline"  # Deadlines

    # Entity categories
    ENTITY_PERSON = "entity_person"  # Information about people
    ENTITY_PLACE = "entity_place"  # Information about places
    ENTITY_ORGANIZATION = "entity_organization"  # Companies, groups
    ENTITY_PRODUCT = "entity_product"  # Products, services
    ENTITY_CONCEPT = "entity_concept"  # Abstract concepts

    # Relationship category
    RELATIONSHIP = "relationship"  # Connections between entities

    # Other
    OTHER = "other"  # Miscellaneous/uncategorized

    @classmethod
    def from_legacy_category(
        cls, legacy_category: str
    ) -> "KnowledgeFactCategory":
        """
        Convert legacy FactCategory to new KnowledgeFactCategory.

        Args:
            legacy_category: Legacy category string

        Returns:
            Corresponding KnowledgeFactCategory
        """
        legacy_mapping = {
            "identity": cls.USER_IDENTITY,
            "location": cls.USER_LOCATION,
            "preferences": cls.USER_PREFERENCES,
            "relationships": cls.USER_RELATIONSHIPS,
            "work": cls.USER_WORK,
            "interests": cls.USER_INTERESTS,
            "skills": cls.USER_SKILLS,
            "goals": cls.USER_GOALS,
            "history": cls.USER_HISTORY,
            "health": cls.USER_HEALTH,
            "other": cls.OTHER,
        }
        return legacy_mapping.get(legacy_category, cls.OTHER)

    @classmethod
    def to_legacy_category(cls, category: "KnowledgeFactCategory") -> str:
        """
        Convert new KnowledgeFactCategory to legacy category string.

        Args:
            category: KnowledgeFactCategory enum

        Returns:
            Legacy category string
        """
        category_mapping = {
            cls.USER_IDENTITY: "identity",
            cls.USER_LOCATION: "location",
            cls.USER_PREFERENCES: "preferences",
            cls.USER_RELATIONSHIPS: "relationships",
            cls.USER_WORK: "work",
            cls.USER_INTERESTS: "interests",
            cls.USER_SKILLS: "skills",
            cls.USER_GOALS: "goals",
            cls.USER_HISTORY: "history",
            cls.USER_HEALTH: "health",
            cls.OTHER: "other",
        }
        return category_mapping.get(category, "other")

    @property
    def is_user_category(self) -> bool:
        """Check if this is a user-specific category."""
        return self.value.startswith("user_")

    @property
    def is_world_category(self) -> bool:
        """Check if this is a world knowledge category."""
        return self.value.startswith("world_")

    @property
    def is_temporal_category(self) -> bool:
        """Check if this is a temporal category."""
        return self.value.startswith("temporal_")

    @property
    def is_entity_category(self) -> bool:
        """Check if this is an entity category."""
        return self.value.startswith("entity_")

    @property
    def is_relationship_category(self) -> bool:
        """Check if this is the relationship category."""
        return self == self.RELATIONSHIP


class KnowledgeSource(Enum):
    """Sources where knowledge facts can originate from."""

    CONVERSATION = "conversation"  # Extracted from conversation
    USER_EDIT = "user_edit"  # Manually added/edited by user
    DOCUMENT = "document"  # Extracted from document
    WEB = "web"  # Retrieved from web
    SYSTEM = "system"  # System-generated
    IMPORT = "import"  # Imported from external source
    MIGRATION = "migration"  # Migrated from legacy system
