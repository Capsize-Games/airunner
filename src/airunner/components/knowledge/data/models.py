"""
Knowledge database models.

Stores factual information, user knowledge, and conversation summaries
for building a comprehensive memory system.
"""

from sqlalchemy import (
    Column,
    String,
    Text,
    Float,
    DateTime,
    Boolean,
    Integer,
    JSON,
)
from sqlalchemy.sql import func
from airunner.components.data.models.base import BaseModel


class KnowledgeFact(BaseModel):
    """
    A factual statement about the user or conversation context.

    This is the foundation of the agent's long-term memory system.
    Facts are extracted from conversations and stored for future recall.

    Attributes:
        text: The factual statement
        category: Category for organization (identity, health, preferences, etc.)
        tags: JSON array of tags for flexible categorization
        confidence: How certain we are about this fact (0.0-1.0)
        source: Where this fact came from (conversation, user_edit, etc.)
        source_conversation_id: If from conversation, which one
        verified: Whether user has verified this fact
        enabled: Whether this fact is active
        created_at: When fact was learned
        updated_at: Last modification
        last_accessed: Last time fact was retrieved (for relevance tracking)
        access_count: Number of times fact has been accessed
    """

    __tablename__ = "knowledge_facts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(Text, nullable=False, index=True)
    category = Column(String(50), nullable=False, default="other", index=True)
    tags = Column(JSON, nullable=True)  # ["health", "pain", "chronic"]
    confidence = Column(Float, nullable=False, default=0.9)
    source = Column(String(50), nullable=False, default="conversation")
    source_conversation_id = Column(Integer, nullable=True)
    verified = Column(Boolean, nullable=False, default=False)
    enabled = Column(Boolean, nullable=False, default=True)

    # Metadata
    metadata_json = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime, nullable=False, default=func.now(), index=True
    )
    updated_at = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )
    last_accessed = Column(DateTime, nullable=True)

    # Usage tracking
    access_count = Column(Integer, nullable=False, default=0)

    def increment_access(self):
        """Track when fact is accessed."""
        from airunner.components.data.session_manager import session_scope

        with session_scope() as session:
            db_fact = (
                session.query(KnowledgeFact).filter_by(id=self.id).first()
            )
            if db_fact:
                db_fact.access_count += 1
                db_fact.last_accessed = func.now()
                session.commit()

    @property
    def tag_list(self):
        """Get tags as list."""
        return self.tags if self.tags else []

    def to_document(self):
        """
        Convert to LangChain Document for RAG.

        Returns:
            Document with fact text and metadata
        """
        from langchain_core.documents import Document

        metadata = {
            "fact_id": self.id,
            "category": self.category,
            "tags": self.tag_list,
            "confidence": self.confidence,
            "source": self.source,
            "verified": self.verified,
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
        }

        return Document(page_content=self.text, metadata=metadata)


class ConversationSummary(BaseModel):
    """
    Summary of a conversation for long-term memory.

    Enables periodic memory recall (weekly, monthly, yearly summaries).

    Attributes:
        conversation_id: Reference to conversation
        summary_text: Text summary of conversation
        key_topics: Main topics discussed
        facts_extracted: Number of facts extracted
        period_type: daily, weekly, monthly, yearly
        period_start: Start of period
        period_end: End of period
        created_at: When summary was created
    """

    __tablename__ = "conversation_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, nullable=True, index=True)
    summary_text = Column(Text, nullable=False)
    key_topics = Column(JSON, nullable=True)  # ["health", "work", "hobbies"]
    facts_extracted = Column(Integer, nullable=False, default=0)

    # Period tracking for multi-level memory
    period_type = Column(
        String(20), nullable=True, index=True
    )  # daily, weekly, monthly, yearly
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)

    created_at = Column(
        DateTime, nullable=False, default=func.now(), index=True
    )

    def to_document(self):
        """Convert to LangChain Document for RAG."""
        from langchain_core.documents import Document

        metadata = {
            "summary_id": self.id,
            "conversation_id": self.conversation_id,
            "period_type": self.period_type,
            "key_topics": self.key_topics,
            "period_start": (
                self.period_start.isoformat() if self.period_start else None
            ),
            "period_end": (
                self.period_end.isoformat() if self.period_end else None
            ),
        }

        return Document(page_content=self.summary_text, metadata=metadata)
