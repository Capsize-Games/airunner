"""Ensure Alembic autogeneration sees the full service schema and drift."""

from __future__ import annotations

import sqlalchemy as sa
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Column, MetaData, String, Table

from airunner_services.database.migration_metadata import (
    migration_context_options,
    service_metadata,
)


def _legacy_llm_tool_metadata(metadata: sa.MetaData) -> MetaData:
    """Build one representative pre-drift table for SQLite comparison."""
    model = metadata.tables["llm_tool"]
    legacy_metadata = MetaData()
    columns = []
    for model_column in model.columns:
        column_type = (
            String() if model_column.name == "usage_count" else model_column.type
        )
        columns.append(
            Column(
                model_column.name,
                column_type,
                primary_key=model_column.primary_key,
                nullable=model_column.nullable,
                autoincrement=(
                    True if model_column.name == "id" else "auto"
                ),
            )
        )
    Table("llm_tool", legacy_metadata, *columns)
    return legacy_metadata


def _llm_tool_changes(diffs: list[tuple]) -> set[str]:
    """Return changed fields for alter-type/default diffs on llm_tool."""
    changed_fields: set[str] = set()
    for diff in diffs:
        if isinstance(diff, list):
            changed_fields.update(_llm_tool_changes(diff))
        elif (
            diff[0] in {"modify_type", "modify_default"}
            and diff[2] == "llm_tool"
        ):
            changed_fields.add(diff[3])
    return changed_fields


def test_service_metadata_registers_complete_service_models() -> None:
    """The Alembic target includes service and companion ORM tables."""
    metadata = service_metadata()
    assert len(metadata.tables) >= 50
    assert "llm_tool" in metadata.tables
    assert "companion_jobs" in metadata.tables
    assert "companion_facts" in metadata.tables


def test_autogenerate_detects_type_and_server_default_drift() -> None:
    """Shared Alembic options detect real type and server-default changes."""
    metadata = service_metadata()
    engine = sa.create_engine("sqlite:///:memory:")
    try:
        _legacy_llm_tool_metadata(metadata).create_all(engine)
        with engine.connect() as connection:
            options = migration_context_options()
            assert options["target_metadata"] is metadata
            assert options["compare_type"] is True
            assert options["compare_server_default"] is True

            context = MigrationContext.configure(connection, opts=options)
            diffs = compare_metadata(context, metadata)
            assert {"usage_count", "created_at"} <= _llm_tool_changes(diffs)

            disabled_context = MigrationContext.configure(
                connection,
                opts={
                    **options,
                    "compare_type": False,
                    "compare_server_default": False,
                },
            )
            disabled_diffs = compare_metadata(disabled_context, metadata)
            assert not _llm_tool_changes(disabled_diffs)
    finally:
        engine.dispose()
