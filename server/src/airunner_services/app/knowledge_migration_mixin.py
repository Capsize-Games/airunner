"""JSON-to-markdown knowledge migration helpers for RuntimeMixin."""

from __future__ import annotations

from pathlib import Path

from airunner_services.knowledge import get_knowledge_base
from airunner_services.database.models.application_settings import (
    ApplicationSettings,
)
from airunner_services.database.session import session_scope
from airunner_services.settings import AIRUNNER_USER_DATA_PATH

_SECTION_MAP = {
    "identity": "Identity",
    "personal": "Identity",
    "work": "Work & Projects",
    "project": "Work & Projects",
    "hobby": "Interests & Hobbies",
    "interest": "Interests & Hobbies",
    "preference": "Preferences",
    "health": "Health & Wellness",
    "relationship": "Relationships",
    "goal": "Goals",
    "other": "Notes",
    "notes": "Notes",
}


class KnowledgeMigrationMixin:
    """Provide JSON-to-markdown knowledge migration helpers."""

    def _run_knowledge_migration_if_needed(self):
        """Run one-time migration from JSON to markdown if needed."""
        try:
            json_path = self._resolve_migration_json_path()
            if json_path is None:
                return
            self._migrate_json_to_markdown(json_path)
            self._mark_migration_complete()
        except Exception as exc:
            self.logger.error(
                "Failed to run knowledge migration: %s. "
                "Migration NOT marked complete - will retry "
                "on next startup.",
                exc,
                exc_info=True,
            )

    def _resolve_migration_json_path(self):
        """Return the JSON path to migrate, or None if not needed."""
        with session_scope() as session:
            settings = (
                session.query(ApplicationSettings)
                .filter_by(id=1)
                .with_for_update()
                .first()
            )
            if not settings:
                self.logger.info("Creating default application settings")
                settings = ApplicationSettings(
                    id=1,
                    knowledge_migrated=False,
                )
                session.add(settings)
                session.commit()
                settings = (
                    session.query(ApplicationSettings)
                    .filter_by(id=1)
                    .with_for_update()
                    .first()
                )
            if settings.knowledge_migrated:
                self.logger.debug("Knowledge migration already completed")
                return None

        knowledge_dir = Path(AIRUNNER_USER_DATA_PATH) / "knowledge"
        json_path = knowledge_dir / "user_facts.json"
        if not json_path.exists():
            with session_scope() as session:
                existing = (
                    session.query(ApplicationSettings)
                    .filter_by(id=1)
                    .with_for_update()
                    .first()
                )
                if existing is not None:
                    existing.knowledge_migrated = True
                    session.commit()
            self.logger.info(
                "No legacy knowledge data found, skipping migration"
            )
            return None

        self.logger.info(
            "Running one-time knowledge migration " "from JSON to markdown..."
        )
        return json_path

    def _migrate_json_to_markdown(self, json_path: Path):
        """Migrate legacy JSON facts to the markdown knowledge base."""
        import json

        try:
            with open(json_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)

            knowledge_base = get_knowledge_base()
            facts = data if isinstance(data, list) else data.get("facts", [])
            migrated = self._process_facts_migration(facts, knowledge_base)

            self.logger.info(
                "Knowledge migration successful: "
                "%s facts migrated to markdown",
                migrated,
            )
            backup_path = json_path.with_suffix(".json.migrated")
            json_path.rename(backup_path)
            self.logger.info("Legacy JSON backed up to: %s", backup_path)
        except Exception as exc:
            self.logger.error(
                "Error during JSON to markdown migration: %s",
                exc,
            )
            raise

    def _process_facts_migration(self, facts, knowledge_base):
        """Iterate facts and add each to the knowledge base."""
        migrated = 0
        for fact_data in facts:
            if isinstance(fact_data, str):
                fact_text = fact_data
                category = "Notes"
            elif isinstance(fact_data, dict):
                fact_text = fact_data.get(
                    "text",
                    fact_data.get("content", ""),
                )
                category = fact_data.get("category", "Notes")
            else:
                continue

            if not fact_text:
                continue
            section = _SECTION_MAP.get(category.lower(), "Notes")
            knowledge_base.add_fact(fact_text, section=section)
            migrated += 1
        return migrated

    def _mark_migration_complete(self):
        """Mark knowledge migration as complete in settings."""
        try:
            with session_scope() as session:
                settings = (
                    session.query(ApplicationSettings).filter_by(id=1).first()
                )
                if settings:
                    settings.knowledge_migrated = True
                    session.commit()
        except Exception as exc:
            self.logger.error(
                "Failed to mark migration complete: %s",
                exc,
                exc_info=True,
            )
