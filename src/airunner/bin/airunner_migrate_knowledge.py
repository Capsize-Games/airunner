#!/usr/bin/env python3
"""
Knowledge System Migration CLI

Migrates user facts from legacy JSON format to database system.
Preserves all data including text, category, confidence, source, timestamp, and metadata.
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import argparse
from airunner.components.knowledge.data.models import KnowledgeFact
from airunner.components.data.session_manager import session_scope
from airunner.settings import AIRUNNER_LOG_LEVEL, AIRUNNER_USER_DATA_PATH
from airunner.utils.application import get_logger


class KnowledgeMigrationError(Exception):
    """Custom exception for migration errors."""


class KnowledgeMigrator:
    """Handles migration of knowledge facts from JSON to database."""

    def __init__(self, json_path: Optional[Path] = None):
        """
        Initialize migrator.

        Args:
            json_path: Path to user_facts.json (default: auto-detect)
        """
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
        if json_path:
            self.json_path = Path(json_path)
        else:
            knowledge_dir = Path(AIRUNNER_USER_DATA_PATH) / "knowledge"
            self.json_path = knowledge_dir / "user_facts.json"

        self.backup_path = self.json_path.with_suffix(".json.backup")
        self.migrated_count = 0
        self.skipped_count = 0
        self.error_count = 0

    def validate_json_file(self) -> bool:
        """
        Validate JSON file exists and is readable.

        Returns:
            True if file is valid

        Raises:
            KnowledgeMigrationError: If file is invalid
        """
        if not self.json_path.exists():
            raise KnowledgeMigrationError(
                f"JSON file not found: {self.json_path}"
            )

        if not self.json_path.is_file():
            raise KnowledgeMigrationError(
                f"Path is not a file: {self.json_path}"
            )

        # Handle empty file (fresh install)
        if self.json_path.stat().st_size == 0:
            self.logger.info(
                "JSON file is empty (fresh install) - no migration needed"
            )
            return True

        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, list):
                    raise KnowledgeMigrationError(
                        "JSON file must contain an array of facts"
                    )
                self.logger.info(f"Found {len(data)} facts in JSON file")
                return True
        except json.JSONDecodeError as e:
            raise KnowledgeMigrationError(f"Invalid JSON format: {e}") from e
        except Exception as e:
            raise KnowledgeMigrationError(
                f"Error reading JSON file: {e}"
            ) from e

    def create_backup(self) -> Path:
        """
        Create backup of JSON file before migration.

        Returns:
            Path to backup file

        Raises:
            KnowledgeMigrationError: If backup fails
        """
        try:
            import shutil

            shutil.copy2(self.json_path, self.backup_path)
            self.logger.info(f"Created backup: {self.backup_path}")
            return self.backup_path
        except Exception as e:
            raise KnowledgeMigrationError(
                f"Failed to create backup: {e}"
            ) from e

    def parse_json_facts(self) -> List[Dict]:
        """
        Parse facts from JSON file.

        Returns:
            List of fact dictionaries

        Raises:
            KnowledgeMigrationError: If parsing fails
        """
        # Handle empty file (fresh install)
        if self.json_path.stat().st_size == 0:
            self.logger.info("JSON file is empty - returning empty fact list")
            return []

        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                facts = json.load(f)

            # Validate each fact has required fields
            for i, fact in enumerate(facts):
                if not isinstance(fact, dict):
                    self.logger.warning(
                        f"Skipping fact #{i}: not a dictionary"
                    )
                    continue
                if "text" not in fact:
                    self.logger.warning(
                        f"Skipping fact #{i}: missing 'text' field"
                    )
                    continue

            return facts
        except Exception as e:
            raise KnowledgeMigrationError(f"Failed to parse facts: {e}") from e

    def fact_exists_in_db(self, text: str) -> bool:
        """
        Check if fact with this text already exists in database.

        Args:
            text: Fact text to check

        Returns:
            True if fact exists
        """
        with session_scope() as session:
            existing = (
                session.query(KnowledgeFact)
                .filter(KnowledgeFact.text == text)
                .first()
            )
            return existing is not None

    def migrate_fact(self, fact_data: Dict) -> Optional[KnowledgeFact]:
        """
        Migrate single fact to database.

        Args:
            fact_data: Fact dictionary from JSON

        Returns:
            Created KnowledgeFact or None if skipped

        Raises:
            KnowledgeMigrationError: If migration fails
        """
        text = fact_data.get("text", "").strip()
        if not text:
            self.logger.warning("Skipping fact with empty text")
            self.skipped_count += 1
            return None

        # Check if already exists
        if self.fact_exists_in_db(text):
            self.logger.debug(f"Fact already exists, skipping: {text[:50]}...")
            self.skipped_count += 1
            return None

        try:
            # Parse category
            category_str = fact_data.get("category", "other")
            if isinstance(category_str, str):
                category = category_str
            else:
                category = "other"

            # Parse timestamp
            timestamp_str = fact_data.get("timestamp")
            if timestamp_str:
                try:
                    created_at = datetime.fromisoformat(timestamp_str)
                except (ValueError, TypeError):
                    created_at = datetime.now()
            else:
                created_at = datetime.now()

            # Create database fact
            with session_scope() as session:
                db_fact = KnowledgeFact(
                    text=text,
                    category=category,
                    confidence=fact_data.get("confidence", 0.9),
                    source=fact_data.get("source", "migration"),
                    verified=False,  # Will be verified by user later
                    enabled=True,
                    metadata_json=fact_data.get("metadata", {}),
                    created_at=created_at,
                    updated_at=created_at,
                )
                session.add(db_fact)
                session.commit()
                session.refresh(db_fact)

                # Detach from session to avoid DetachedInstanceError
                session.expunge(db_fact)

                self.migrated_count += 1
                self.logger.debug(f"Migrated fact: {text[:50]}...")
                return db_fact

        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Error migrating fact '{text[:50]}...': {e}")
            return None

    def migrate_all(
        self, dry_run: bool = False, skip_backup: bool = False
    ) -> Dict[str, int]:
        """
        Migrate all facts from JSON to database.

        Args:
            dry_run: If True, don't actually migrate (just validate)
            skip_backup: If True, skip creating backup

        Returns:
            Dictionary with migration statistics

        Raises:
            KnowledgeMigrationError: If migration fails
        """
        self.logger.info("Starting knowledge migration...")

        # Validate JSON file
        self.validate_json_file()

        # Create backup
        if not dry_run and not skip_backup:
            self.create_backup()

        # Parse facts
        facts = self.parse_json_facts()
        self.logger.info(f"Parsed {len(facts)} facts from JSON")

        if dry_run:
            self.logger.info("DRY RUN - No changes will be made")
            # Just validate each fact
            for fact in facts:
                if not isinstance(fact, dict):
                    self.error_count += 1
                elif "text" not in fact:
                    self.error_count += 1
                elif not fact.get("text", "").strip():
                    self.skipped_count += 1
                else:
                    self.migrated_count += 1
        else:
            # Migrate each fact
            for fact in facts:
                self.migrate_fact(fact)

        # Print summary
        stats = {
            "total": len(facts),
            "migrated": self.migrated_count,
            "skipped": self.skipped_count,
            "errors": self.error_count,
        }

        self.logger.info("\n" + "=" * 50)
        self.logger.info("Migration Summary:")
        self.logger.info(f"  Total facts:     {stats['total']}")
        self.logger.info(f"  Migrated:        {stats['migrated']}")
        self.logger.info(f"  Skipped:         {stats['skipped']}")
        self.logger.info(f"  Errors:          {stats['errors']}")
        self.logger.info("=" * 50 + "\n")

        if not dry_run and stats["migrated"] > 0:
            self.logger.info("✅ Migration completed successfully!")
            self.logger.info(f"Backup saved to: {self.backup_path}")

        return stats


def main():
    """Main CLI entry point."""
    logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

    parser = argparse.ArgumentParser(
        description="Migrate knowledge facts from JSON to database"
    )
    parser.add_argument(
        "--json-path",
        type=Path,
        help="Path to user_facts.json (default: auto-detect)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate without making changes",
    )
    parser.add_argument(
        "--skip-backup",
        action="store_true",
        help="Skip creating backup file",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    try:
        migrator = KnowledgeMigrator(json_path=args.json_path)
        stats = migrator.migrate_all(
            dry_run=args.dry_run, skip_backup=args.skip_backup
        )

        # Exit with appropriate code
        if stats["errors"] > 0:
            logger.warning(
                "⚠️  Migration completed with errors. Check logs above."
            )
            sys.exit(1)
        elif stats["migrated"] == 0:
            logger.info("ℹ️  No facts to migrate.")
            sys.exit(0)
        else:
            sys.exit(0)

    except KnowledgeMigrationError as e:
        logger.error(f"❌ Migration failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Migration cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
