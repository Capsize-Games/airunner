"""
Knowledge and Memory Manager

Manages the agent's comprehensive memory system including:
- Short-term memory (current conversation)
- Fact recall (from knowledge base via RAG)
- Periodic summaries (daily, weekly, monthly, yearly)
- User knowledge CRUD operations
"""
from typing import List, Dict, Optional, Union
from datetime import datetime, timedelta

from langchain_core.vectorstores import InMemoryVectorStore

from airunner.components.knowledge.data.models import (
    KnowledgeFact,
    ConversationSummary,
)
from airunner.components.data.session_manager import session_scope
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class KnowledgeMemoryManager:
    """
    Comprehensive memory system for the AI agent.

    Provides multiple "memory banks" similar to human memory:
    - Short-term: Current conversation context
    - Recall: RAG-based retrieval of facts
    - Periodic: Summaries over time (week, month, year)
    """

    def __init__(self, embeddings=None):
        """
        Initialize knowledge memory manager.

        Args:
            embeddings: LangChain embeddings model for RAG
        """
        self.logger = logger
        self.embeddings = embeddings
        self.vector_store: Optional[InMemoryVectorStore] = None

        if self.embeddings:
            self._initialize_vector_store()

    def _initialize_vector_store(self):
        """Initialize vector store with existing facts."""
        try:
            self.vector_store = InMemoryVectorStore(self.embeddings)

            # Load all enabled facts into vector store
            facts = self.get_all_facts(enabled_only=True)
            if facts:
                documents = [fact.to_document() for fact in facts]
                self.vector_store.add_documents(documents)
                self.logger.info(
                    f"Loaded {len(facts)} facts into vector store"
                )
        except Exception as e:
            self.logger.error(f"Failed to initialize vector store: {e}")
            self.vector_store = None

    def refresh_vector_store(self):
        """Refresh vector store with latest facts."""
        if not self.embeddings:
            return

        try:
            self.vector_store = InMemoryVectorStore(self.embeddings)
            facts = self.get_all_facts(enabled_only=True)
            if facts:
                documents = [fact.to_document() for fact in facts]
                self.vector_store.add_documents(documents)
                self.logger.info(
                    f"Refreshed vector store with {len(facts)} facts"
                )
        except Exception as e:
            self.logger.error(f"Failed to refresh vector store: {e}")

    # ========================================================================
    # Fact Management (CRUD Operations)
    # ========================================================================

    def add_fact(
        self,
        text: str,
        category: str = "other",
        tags: Optional[List[str]] = None,
        confidence: float = 0.9,
        source: str = "conversation",
        conversation_id: Optional[int] = None,
        verified: bool = False,
    ) -> KnowledgeFact:
        """
        Add a new fact to the knowledge base.

        Args:
            text: The factual statement
            category: Category (identity, health, preferences, etc.)
            tags: List of tags for flexible categorization
            confidence: Confidence score (0.0-1.0)
            source: Where fact came from
            conversation_id: Source conversation ID
            verified: Whether user has verified this

        Returns:
            Created KnowledgeFact object
        """
        with session_scope() as session:
            fact = KnowledgeFact(
                text=text,
                category=category,
                tags=tags,
                confidence=confidence,
                source=source,
                source_conversation_id=conversation_id,
                verified=verified,
                enabled=True,
            )
            session.add(fact)
            session.commit()
            session.refresh(fact)

            # Detach from session to prevent DetachedInstanceError
            session.expunge(fact)

            self.logger.info(f"Added fact: {text[:50]}...")

            # Add to vector store
            if self.vector_store:
                self.vector_store.add_documents([fact.to_document()])

            return fact

    def update_fact(
        self,
        fact_id: int,
        text: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        confidence: Optional[float] = None,
        verified: Optional[bool] = None,
        enabled: Optional[bool] = None,
    ) -> Optional[KnowledgeFact]:
        """
        Update an existing fact.

        Args:
            fact_id: ID of fact to update
            text: New text (optional)
            category: New category (optional)
            tags: New tags (optional)
            confidence: New confidence (optional)
            verified: New verified status (optional)
            enabled: New enabled status (optional)

        Returns:
            Updated fact or None if not found
        """
        with session_scope() as session:
            fact = session.query(KnowledgeFact).filter_by(id=fact_id).first()
            if not fact:
                return None

            if text is not None:
                fact.text = text
            if category is not None:
                fact.category = category
            if tags is not None:
                fact.tags = tags
            if confidence is not None:
                fact.confidence = confidence
            if verified is not None:
                fact.verified = verified
            if enabled is not None:
                fact.enabled = enabled

            session.commit()
            session.refresh(fact)

            self.logger.info(f"Updated fact {fact_id}")

            # Refresh vector store
            self.refresh_vector_store()

            return fact

    def delete_fact(self, fact_id: int) -> bool:
        """
        Delete a fact.

        Args:
            fact_id: ID of fact to delete

        Returns:
            True if deleted, False if not found
        """
        with session_scope() as session:
            fact = session.query(KnowledgeFact).filter_by(id=fact_id).first()
            if not fact:
                return False

            session.delete(fact)
            session.commit()

            self.logger.info(f"Deleted fact {fact_id}")

            # Refresh vector store
            self.refresh_vector_store()

            return True

    def get_fact(self, fact_id: int) -> Optional[KnowledgeFact]:
        """Get a single fact by ID."""
        with session_scope() as session:
            fact = session.query(KnowledgeFact).filter_by(id=fact_id).first()
            if fact:
                fact.increment_access()
            return fact

    def get_all_facts(
        self,
        category: Optional[Union[str, List[str]]] = None,
        tags: Optional[List[str]] = None,
        enabled_only: bool = False,
        verified_only: bool = False,
        source: Optional[Union[str, List[str]]] = None,
    ) -> List[KnowledgeFact]:
        """
        Get all facts with optional filtering.

        Args:
            category: Filter by category (single string or list of categories)
            tags: Filter by tags (any match)
            enabled_only: Only get enabled facts
            verified_only: Only get verified facts
            source: Filter by source (single string or list of sources)

        Returns:
            List of facts
        """
        with session_scope() as session:
            query = session.query(KnowledgeFact)

            if category:
                if isinstance(category, str):
                    query = query.filter_by(category=category)
                elif isinstance(category, list):
                    query = query.filter(KnowledgeFact.category.in_(category))

            if source:
                if isinstance(source, str):
                    query = query.filter_by(source=source)
                elif isinstance(source, list):
                    query = query.filter(KnowledgeFact.source.in_(source))

            if enabled_only:
                query = query.filter_by(enabled=True)
            if verified_only:
                query = query.filter_by(verified=True)
            if tags:
                # Filter by any tag match
                # This is a simple implementation - for production, consider using PostgreSQL arrays
                for tag in tags:
                    query = query.filter(KnowledgeFact.tags.contains(tag))

            facts = query.order_by(KnowledgeFact.created_at.desc()).all()

            # Detach from session to prevent DetachedInstanceError
            for fact in facts:
                session.expunge(fact)

            return facts

    def get_facts_by_category_type(
        self,
        is_user: bool = False,
        is_world: bool = False,
        is_temporal: bool = False,
        is_entity: bool = False,
        enabled_only: bool = True,
    ) -> List[KnowledgeFact]:
        """
        Get facts by category type (user, world, temporal, entity).

        Args:
            is_user: Get user-specific facts
            is_world: Get world knowledge facts
            is_temporal: Get temporal facts
            is_entity: Get entity facts
            enabled_only: Only get enabled facts

        Returns:
            List of facts matching the category type
        """
        from airunner.components.knowledge.enums import KnowledgeFactCategory

        categories = []

        if is_user:
            categories.extend(
                [
                    cat.value
                    for cat in KnowledgeFactCategory
                    if cat.is_user_category
                ]
            )
        if is_world:
            categories.extend(
                [
                    cat.value
                    for cat in KnowledgeFactCategory
                    if cat.is_world_category
                ]
            )
        if is_temporal:
            categories.extend(
                [
                    cat.value
                    for cat in KnowledgeFactCategory
                    if cat.is_temporal_category
                ]
            )
        if is_entity:
            categories.extend(
                [
                    cat.value
                    for cat in KnowledgeFactCategory
                    if cat.is_entity_category
                ]
            )

        return self.get_all_facts(
            category=categories, enabled_only=enabled_only
        )

    # ========================================================================
    # RAG-based Memory Recall
    # ========================================================================

    def recall_facts(self, query: str, k: int = 5) -> List[KnowledgeFact]:
        """
        Recall relevant facts using RAG similarity search.

        Args:
            query: Search query
            k: Number of facts to retrieve

        Returns:
            List of relevant facts
        """
        if not self.vector_store:
            self.logger.warning("Vector store not initialized")
            return []

        try:
            # Search vector store
            documents = self.vector_store.similarity_search(query, k=k)

            # Convert back to facts
            fact_ids = [doc.metadata.get("fact_id") for doc in documents]

            with session_scope() as session:
                facts = []
                for fact_id in fact_ids:
                    if fact_id:
                        fact = (
                            session.query(KnowledgeFact)
                            .filter_by(id=fact_id)
                            .first()
                        )
                        if fact:
                            fact.increment_access()
                            facts.append(fact)

                return facts
        except Exception as e:
            self.logger.error(f"Error during recall: {e}")
            return []

    def get_context_for_conversation(
        self,
        query: str = "",
        include_recent: int = 10,
        include_recall: int = 5,
    ) -> str:
        """
        Get comprehensive context for a conversation.

        Combines:
        - Recent facts (short-term memory)
        - Relevant facts from RAG (recall memory)
        - Periodic summaries

        Args:
            query: Current conversation topic
            include_recent: Number of recent facts
            include_recall: Number of recalled facts

        Returns:
            Formatted context string
        """
        context_parts = []

        # Get recent facts (short-term memory)
        recent_facts = self.get_all_facts(enabled_only=True)[:include_recent]
        if recent_facts:
            context_parts.append("## Recent Knowledge")
            for fact in recent_facts:
                verified_mark = "✓" if fact.verified else ""
                context_parts.append(f"- {fact.text} {verified_mark}")

        # Get relevant facts via RAG (recall memory)
        if query and self.vector_store:
            recalled_facts = self.recall_facts(query, k=include_recall)
            if recalled_facts:
                context_parts.append("\n## Relevant Recalled Knowledge")
                for fact in recalled_facts:
                    if fact not in recent_facts:  # Avoid duplicates
                        verified_mark = "✓" if fact.verified else ""
                        context_parts.append(f"- {fact.text} {verified_mark}")

        # Get periodic summaries
        summaries = self.get_periodic_summaries()
        if summaries:
            context_parts.append("\n## Memory Summaries")
            for period_type, summary in summaries.items():
                context_parts.append(f"**{period_type.title()}:** {summary}")

        return "\n".join(context_parts)

    # ========================================================================
    # Periodic Summaries
    # ========================================================================

    def create_summary(
        self,
        summary_text: str,
        key_topics: Optional[List[str]] = None,
        facts_extracted: int = 0,
        conversation_id: Optional[int] = None,
        period_type: Optional[str] = None,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> ConversationSummary:
        """
        Create a conversation summary.

        Args:
            summary_text: Summary text
            key_topics: Main topics
            facts_extracted: Number of facts extracted
            conversation_id: Source conversation
            period_type: daily, weekly, monthly, yearly
            period_start: Start of period
            period_end: End of period

        Returns:
            Created summary
        """
        with session_scope() as session:
            summary = ConversationSummary(
                conversation_id=conversation_id,
                summary_text=summary_text,
                key_topics=key_topics,
                facts_extracted=facts_extracted,
                period_type=period_type,
                period_start=period_start,
                period_end=period_end,
            )
            session.add(summary)
            session.commit()
            session.refresh(summary)

            self.logger.info(
                f"Created {period_type or 'conversation'} summary"
            )
            return summary

    def get_periodic_summaries(
        self,
        include_weekly: bool = True,
        include_monthly: bool = True,
        include_yearly: bool = True,
    ) -> Dict[str, str]:
        """
        Get recent periodic summaries.

        Args:
            include_weekly: Include last week summary
            include_monthly: Include last month summary
            include_yearly: Include last year summary

        Returns:
            Dict with period_type: summary_text
        """
        summaries = {}
        now = datetime.now()

        with session_scope() as session:
            if include_weekly:
                week_ago = now - timedelta(days=7)
                weekly = (
                    session.query(ConversationSummary)
                    .filter_by(period_type="weekly")
                    .filter(ConversationSummary.period_start >= week_ago)
                    .order_by(ConversationSummary.created_at.desc())
                    .first()
                )
                if weekly:
                    summaries["weekly"] = weekly.summary_text

            if include_monthly:
                month_ago = now - timedelta(days=30)
                monthly = (
                    session.query(ConversationSummary)
                    .filter_by(period_type="monthly")
                    .filter(ConversationSummary.period_start >= month_ago)
                    .order_by(ConversationSummary.created_at.desc())
                    .first()
                )
                if monthly:
                    summaries["monthly"] = monthly.summary_text

            if include_yearly:
                year_ago = now - timedelta(days=365)
                yearly = (
                    session.query(ConversationSummary)
                    .filter_by(period_type="yearly")
                    .filter(ConversationSummary.period_start >= year_ago)
                    .order_by(ConversationSummary.created_at.desc())
                    .first()
                )
                if yearly:
                    summaries["yearly"] = yearly.summary_text

        return summaries

    # ========================================================================
    # Relationship Queries
    # ========================================================================

    def get_fact_entities(self, fact_id: int) -> List[Dict]:
        """
        Get all entities mentioned in a fact.

        Args:
            fact_id: ID of the fact

        Returns:
            List of entity dictionaries with name, type, confidence
        """
        from airunner.components.knowledge.data.knowledge_relationship import (
            KnowledgeRelationship,
        )

        with session_scope() as session:
            relationships = (
                session.query(KnowledgeRelationship)
                .filter_by(source_fact_id=fact_id)
                .filter(KnowledgeRelationship.entity_name.isnot(None))
                .all()
            )

            entities = [
                {
                    "name": rel.entity_name,
                    "type": rel.entity_type,
                    "confidence": rel.confidence,
                }
                for rel in relationships
            ]

        return entities

    def get_facts_by_entity(
        self, entity_name: str, entity_type: Optional[str] = None
    ) -> List[KnowledgeFact]:
        """
        Get all facts that mention a specific entity.

        Args:
            entity_name: Name of the entity
            entity_type: Optional type filter (person, place, etc.)

        Returns:
            List of facts mentioning this entity
        """
        from airunner.components.knowledge.data.knowledge_relationship import (
            KnowledgeRelationship,
        )

        with session_scope() as session:
            query = (
                session.query(KnowledgeFact)
                .join(
                    KnowledgeRelationship,
                    KnowledgeFact.id == KnowledgeRelationship.source_fact_id,
                )
                .filter(KnowledgeRelationship.entity_name == entity_name)
            )

            if entity_type:
                query = query.filter(
                    KnowledgeRelationship.entity_type == entity_type
                )

            facts = query.all()

            # Detach from session
            for fact in facts:
                session.expunge(fact)

        return facts

    def get_related_facts(
        self, fact_id: int, relationship_types: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Get facts related to a given fact.

        Args:
            fact_id: ID of the source fact
            relationship_types: Optional filter for relationship types
                (contradicts, updates, supports, relates_to)

        Returns:
            List of dicts with {fact: KnowledgeFact, relationship_type: str}
        """
        from airunner.components.knowledge.data.knowledge_relationship import (
            KnowledgeRelationship,
        )

        with session_scope() as session:
            query = (
                session.query(KnowledgeFact, KnowledgeRelationship)
                .join(
                    KnowledgeRelationship,
                    KnowledgeFact.id == KnowledgeRelationship.target_fact_id,
                )
                .filter(KnowledgeRelationship.source_fact_id == fact_id)
                .filter(KnowledgeRelationship.target_fact_id.isnot(None))
            )

            if relationship_types:
                query = query.filter(
                    KnowledgeRelationship.relationship_type.in_(
                        relationship_types
                    )
                )

            results = query.all()

            # Detach and format results
            related = []
            for fact, relationship in results:
                session.expunge(fact)
                related.append(
                    {
                        "fact": fact,
                        "relationship_type": relationship.relationship_type,
                        "confidence": relationship.confidence,
                    }
                )

        return related

    def add_fact_relationship(
        self,
        source_fact_id: int,
        target_fact_id: int,
        relationship_type: str,
        confidence: float = 0.9,
    ) -> bool:
        """
        Create a relationship between two facts.

        Args:
            source_fact_id: ID of source fact
            target_fact_id: ID of target fact
            relationship_type: Type of relationship (contradicts, updates,
                supports, relates_to)
            confidence: Confidence in this relationship (0.0-1.0)

        Returns:
            True if relationship was created
        """
        from airunner.components.knowledge.data.knowledge_relationship import (
            KnowledgeRelationship,
        )

        try:
            with session_scope() as session:
                # Check if relationship already exists
                existing = (
                    session.query(KnowledgeRelationship)
                    .filter_by(
                        source_fact_id=source_fact_id,
                        target_fact_id=target_fact_id,
                        relationship_type=relationship_type,
                    )
                    .first()
                )

                if existing:
                    self.logger.debug(
                        f"Fact relationship already exists: {source_fact_id} -> {target_fact_id}"
                    )
                    return False

                # Create new relationship
                relationship = KnowledgeRelationship(
                    source_fact_id=source_fact_id,
                    target_fact_id=target_fact_id,
                    relationship_type=relationship_type,
                    confidence=confidence,
                )

                session.add(relationship)
                session.commit()

                self.logger.info(
                    f"Created fact relationship: {source_fact_id} -[{relationship_type}]-> {target_fact_id}"
                )
                return True

        except Exception as e:
            self.logger.error(
                f"Error creating fact relationship: {e}", exc_info=True
            )
            return False
