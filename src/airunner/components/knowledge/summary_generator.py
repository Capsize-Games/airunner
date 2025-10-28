"""
Conversation summary generator for knowledge system.

Creates periodic summaries of conversations and extracted facts
for long-term memory and context preservation.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict

from airunner.components.knowledge.knowledge_memory_manager import (
    KnowledgeMemoryManager,
)
from airunner.components.knowledge.data.models import (
    KnowledgeFact,
    ConversationSummary,
)
from airunner.components.data.session_manager import session_scope


class SummaryPeriod:
    """Summary period types."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class SummaryGenerator:
    """
    Generates periodic summaries of conversations and knowledge.

    Creates daily, weekly, and monthly summaries to preserve
    context and track knowledge evolution over time.

    Attributes:
        km: KnowledgeMemoryManager instance
    """

    def __init__(self):
        """Initialize summary generator."""
        self.logger = logging.getLogger(__name__)
        self.km = KnowledgeMemoryManager()

    def generate_summary(
        self,
        period: str = SummaryPeriod.DAILY,
        conversation_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Optional[ConversationSummary]:
        """
        Generate a summary for the specified period.

        Args:
            period: Summary period (daily, weekly, monthly)
            conversation_id: Optional conversation to summarize
            start_date: Start of summary period (auto-calculated if None)
            end_date: End of summary period (defaults to now)

        Returns:
            ConversationSummary or None if no facts in period
        """
        # Calculate date range if not provided
        if end_date is None:
            end_date = datetime.now()

        if start_date is None:
            start_date = self._calculate_start_date(period, end_date)

        # Get facts from the period
        facts = self._get_facts_in_period(
            start_date, end_date, conversation_id
        )

        if not facts:
            self.logger.info(
                f"No facts found for {period} summary ({start_date} to {end_date})"
            )
            return None

        # Generate summary text
        summary_text = self._create_summary_text(facts, period)

        # Create summary metadata
        metadata = {
            "period": period,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "fact_count": len(facts),
            "categories": self._categorize_facts(facts),
        }

        # Save summary to database
        with session_scope() as session:
            summary = ConversationSummary(
                conversation_id=conversation_id,
                summary=summary_text,
                period=period,
                start_date=start_date,
                end_date=end_date,
                metadata_json=metadata,
            )
            session.add(summary)
            session.commit()

            self.logger.info(
                f"Generated {period} summary with {len(facts)} facts"
            )

            return summary

    def _calculate_start_date(
        self, period: str, end_date: datetime
    ) -> datetime:
        """
        Calculate start date based on period type.

        Args:
            period: Summary period
            end_date: End date

        Returns:
            Start date for the period
        """
        if period == SummaryPeriod.DAILY:
            return end_date - timedelta(days=1)
        elif period == SummaryPeriod.WEEKLY:
            return end_date - timedelta(weeks=1)
        elif period == SummaryPeriod.MONTHLY:
            return end_date - timedelta(days=30)
        else:
            return end_date - timedelta(days=1)

    def _get_facts_in_period(
        self,
        start_date: datetime,
        end_date: datetime,
        conversation_id: Optional[int] = None,
    ) -> List[KnowledgeFact]:
        """
        Get all facts created in the specified period.

        Args:
            start_date: Period start
            end_date: Period end
            conversation_id: Optional conversation filter

        Returns:
            List of facts in the period
        """
        with session_scope() as session:
            query = session.query(KnowledgeFact).filter(
                KnowledgeFact.created_at >= start_date,
                KnowledgeFact.created_at <= end_date,
                KnowledgeFact.enabled.is_(True),
            )

            if conversation_id:
                query = query.filter(
                    KnowledgeFact.conversation_id == conversation_id
                )

            facts = query.order_by(KnowledgeFact.created_at).all()
            return facts

    def _create_summary_text(
        self, facts: List[KnowledgeFact], period: str
    ) -> str:
        """
        Create human-readable summary text from facts.

        Args:
            facts: List of facts to summarize
            period: Summary period

        Returns:
            Summary text
        """
        summary_parts = [f"Summary for {period} period:"]
        summary_parts.append(f"Total facts: {len(facts)}")

        # Group by category
        categories = self._categorize_facts(facts)
        if categories:
            summary_parts.append("\nBy category:")
            for category, count in sorted(
                categories.items(), key=lambda x: x[1], reverse=True
            ):
                summary_parts.append(
                    f"  - {category.replace('_', ' ').title()}: {count} facts"
                )

        # Add key facts (verified high-confidence)
        key_facts = [f for f in facts if f.verified and f.confidence > 0.85]
        if key_facts:
            summary_parts.append(f"\nKey facts ({len(key_facts)}):")
            for fact in key_facts[:5]:  # Top 5
                summary_parts.append(f"  - {fact.text}")

        return "\n".join(summary_parts)

    def _categorize_facts(self, facts: List[KnowledgeFact]) -> Dict[str, int]:
        """
        Count facts by category.

        Args:
            facts: List of facts

        Returns:
            Dict mapping category to count
        """
        categories: Dict[str, int] = {}
        for fact in facts:
            category = fact.category or "other"
            categories[category] = categories.get(category, 0) + 1
        return categories

    def get_recent_summaries(
        self,
        period: str = SummaryPeriod.DAILY,
        conversation_id: Optional[int] = None,
        limit: int = 5,
    ) -> List[ConversationSummary]:
        """
        Get recent summaries for a period type.

        Args:
            period: Summary period type
            conversation_id: Optional conversation filter
            limit: Maximum summaries to return

        Returns:
            List of recent summaries
        """
        with session_scope() as session:
            query = session.query(ConversationSummary).filter(
                ConversationSummary.period == period
            )

            if conversation_id:
                query = query.filter(
                    ConversationSummary.conversation_id == conversation_id
                )

            summaries = (
                query.order_by(ConversationSummary.end_date.desc())
                .limit(limit)
                .all()
            )

            return summaries

    def should_generate_summary(
        self, period: str, conversation_id: Optional[int] = None
    ) -> bool:
        """
        Check if a new summary should be generated.

        Args:
            period: Summary period type
            conversation_id: Optional conversation ID

        Returns:
            True if summary should be generated
        """
        # Get most recent summary for this period
        summaries = self.get_recent_summaries(period, conversation_id, limit=1)

        if not summaries:
            return True

        last_summary = summaries[0]
        now = datetime.now()

        # Check if enough time has passed since last summary
        if period == SummaryPeriod.DAILY:
            return (now - last_summary.end_date).days >= 1
        elif period == SummaryPeriod.WEEKLY:
            return (now - last_summary.end_date).days >= 7
        elif period == SummaryPeriod.MONTHLY:
            return (now - last_summary.end_date).days >= 30

        return True
