"""
Knowledge browser export and bulk operations utilities.

Provides export to JSON/CSV and bulk operations for knowledge facts.
"""

import json
import csv
import logging
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from airunner.components.knowledge.data.models import KnowledgeFact
from airunner.components.data.session_manager import session_scope


logger = logging.getLogger(__name__)


class KnowledgeExporter:
    """
    Export knowledge facts to various formats.

    Supports JSON, CSV exports with filtering and backup functionality.
    """

    def export_to_json(
        self,
        output_path: str,
        category: Optional[str] = None,
        verified_only: bool = False,
    ) -> int:
        """
        Export facts to JSON format.

        Args:
            output_path: Path to output JSON file
            category: Optional category filter
            verified_only: Only export verified facts

        Returns:
            Number of facts exported
        """
        with session_scope() as session:
            query = session.query(KnowledgeFact).filter(
                KnowledgeFact.enabled.is_(True)
            )

            if category:
                query = query.filter(KnowledgeFact.category == category)

            if verified_only:
                query = query.filter(KnowledgeFact.verified.is_(True))

            facts = query.all()

            # Convert to dictionaries
            export_data = []
            for fact in facts:
                fact_dict = {
                    "id": fact.id,
                    "text": fact.text,
                    "category": fact.category,
                    "tags": fact.tag_list,
                    "confidence": fact.confidence,
                    "verified": fact.verified,
                    "source": fact.source,
                    "created_at": (
                        fact.created_at.isoformat()
                        if fact.created_at
                        else None
                    ),
                    "access_count": fact.access_count,
                }
                export_data.append(fact_dict)

            # Write to file
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Exported {len(facts)} facts to {output_path}")
            return len(facts)

    def export_to_csv(
        self,
        output_path: str,
        category: Optional[str] = None,
        verified_only: bool = False,
    ) -> int:
        """
        Export facts to CSV format.

        Args:
            output_path: Path to output CSV file
            category: Optional category filter
            verified_only: Only export verified facts

        Returns:
            Number of facts exported
        """
        with session_scope() as session:
            query = session.query(KnowledgeFact).filter(
                KnowledgeFact.enabled.is_(True)
            )

            if category:
                query = query.filter(KnowledgeFact.category == category)

            if verified_only:
                query = query.filter(KnowledgeFact.verified.is_(True))

            facts = query.all()

            # Write to CSV
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)

                # Header
                writer.writerow(
                    [
                        "ID",
                        "Text",
                        "Category",
                        "Tags",
                        "Confidence",
                        "Verified",
                        "Source",
                        "Created",
                        "Access Count",
                    ]
                )

                # Data rows
                for fact in facts:
                    writer.writerow(
                        [
                            fact.id,
                            fact.text,
                            fact.category or "",
                            ", ".join(fact.tag_list) if fact.tag_list else "",
                            fact.confidence,
                            fact.verified,
                            fact.source or "",
                            (
                                fact.created_at.isoformat()
                                if fact.created_at
                                else ""
                            ),
                            fact.access_count,
                        ]
                    )

            logger.info(f"Exported {len(facts)} facts to {output_path}")
            return len(facts)

    def create_backup(self, backup_dir: Optional[str] = None) -> str:
        """
        Create a timestamped backup of all facts.

        Args:
            backup_dir: Directory for backups (default: ./backups)

        Returns:
            Path to backup file
        """
        if backup_dir is None:
            backup_dir = "./backups"

        backup_path = Path(backup_dir)
        backup_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"knowledge_backup_{timestamp}.json"
        output_path = backup_path / filename

        count = self.export_to_json(str(output_path))

        logger.info(f"Created backup with {count} facts at {output_path}")

        return str(output_path)


class KnowledgeBulkOperations:
    """
    Bulk operations on knowledge facts.

    Supports bulk delete, verify, and categorize operations.
    """

    def bulk_delete(self, fact_ids: List[int]) -> int:
        """
        Delete multiple facts by ID.

        Args:
            fact_ids: List of fact IDs to delete

        Returns:
            Number of facts deleted
        """
        with session_scope() as session:
            deleted_count = (
                session.query(KnowledgeFact)
                .filter(KnowledgeFact.id.in_(fact_ids))
                .delete(synchronize_session=False)
            )

            logger.info(f"Bulk deleted {deleted_count} facts")
            return deleted_count

    def bulk_verify(self, fact_ids: List[int], verified: bool = True) -> int:
        """
        Verify or unverify multiple facts.

        Args:
            fact_ids: List of fact IDs
            verified: True to verify, False to unverify

        Returns:
            Number of facts updated
        """
        with session_scope() as session:
            updated_count = (
                session.query(KnowledgeFact)
                .filter(KnowledgeFact.id.in_(fact_ids))
                .update({"verified": verified}, synchronize_session=False)
            )

            logger.info(
                f"Bulk {'verified' if verified else 'unverified'} {updated_count} facts"
            )
            return updated_count

    def bulk_categorize(self, fact_ids: List[int], category: str) -> int:
        """
        Change category for multiple facts.

        Args:
            fact_ids: List of fact IDs
            category: New category

        Returns:
            Number of facts updated
        """
        with session_scope() as session:
            updated_count = (
                session.query(KnowledgeFact)
                .filter(KnowledgeFact.id.in_(fact_ids))
                .update({"category": category}, synchronize_session=False)
            )

            logger.info(
                f"Bulk categorized {updated_count} facts to '{category}'"
            )
            return updated_count

    def bulk_enable_disable(
        self, fact_ids: List[int], enabled: bool = True
    ) -> int:
        """
        Enable or disable multiple facts.

        Args:
            fact_ids: List of fact IDs
            enabled: True to enable, False to disable

        Returns:
            Number of facts updated
        """
        with session_scope() as session:
            updated_count = (
                session.query(KnowledgeFact)
                .filter(KnowledgeFact.id.in_(fact_ids))
                .update({"enabled": enabled}, synchronize_session=False)
            )

            logger.info(
                f"Bulk {'enabled' if enabled else 'disabled'} {updated_count} facts"
            )
            return updated_count
