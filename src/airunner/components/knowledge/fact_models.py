"""Data models for knowledge base entries."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class FactCategory(Enum):
    """Categories for organizing user facts."""

    IDENTITY = "identity"  # Name, age, gender, etc.
    LOCATION = "location"  # Where user lives, works
    PREFERENCES = "preferences"  # Likes, dislikes, habits
    RELATIONSHIPS = "relationships"  # Family, friends
    WORK = "work"  # Job, company, projects
    INTERESTS = "interests"  # Hobbies, topics of interest
    SKILLS = "skills"  # What user can do
    GOALS = "goals"  # What user wants to achieve
    HISTORY = "history"  # Past events, experiences
    HEALTH = "health"  # Medical conditions, symptoms, health status
    OTHER = "other"  # Miscellaneous


@dataclass
class Fact:
    """
    A single factual statement about the user.

    Attributes:
        text: The factual statement
        category: Categorization for organization
        confidence: How certain we are (0.0-1.0)
        source: Where this fact came from
        timestamp: When it was learned
        metadata: Additional context
    """

    text: str
    category: FactCategory = FactCategory.OTHER
    confidence: float = 0.9
    source: str = "conversation"
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "text": self.text,
            "category": self.category.value,
            "confidence": self.confidence,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Fact":
        """Create from dictionary."""
        return cls(
            text=data["text"],
            category=FactCategory(data.get("category", "other")),
            confidence=data.get("confidence", 0.9),
            source=data.get("source", "conversation"),
            timestamp=(
                datetime.fromisoformat(data["timestamp"])
                if "timestamp" in data
                else datetime.now()
            ),
            metadata=data.get("metadata", {}),
        )


@dataclass
class DocumentSummary:
    """
    Multi-level summary of a document for efficient retrieval.

    Attributes:
        doc_id: Unique identifier
        title: Document title
        one_line: Single sentence summary
        paragraph: Paragraph summary
        key_concepts: Main concepts/topics
        full_path: Path to full document
    """

    doc_id: str
    title: str
    one_line: str
    paragraph: str
    key_concepts: List[str] = field(default_factory=list)
    full_path: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)
