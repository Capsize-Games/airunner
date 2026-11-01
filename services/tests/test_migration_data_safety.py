"""Regression coverage for irreversible Alembic downgrades and NULL preservation."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.orm import Session

from airunner_services.database.models.conversation import Conversation
from airunner_services.database.models.openvoice_settings import OpenVoiceSettings


_IRREVERSIBLE_DOWNGRADES = [
    ("2d6569089de6_remove_tts_settings", "tts_settings"),
    ("3b1030ac9b9c_remove_splitter_settings", "splitter_settings"),
    ("50e125c2e188_remove_window_settings", "window_settings"),
    ("7e840c47b899_remove_tab_table", "tabs"),
    ("9d76c1e50d8f_remove_enabled_col_from_rag_settings", "rag_settings"),
    (
        "b96406b64944_remove_bot_mood_and_bot_mood_emoji_",
        Conversation.__tablename__,
    ),
    ("c42b9a3d807a_remove_nsfw", "application_settings"),
    (
        "2a7206a1ff79_add_expression_parameters_to_openvoice_",
        "openvoice_settings",
    ),
]


def _snapshot(connection: sa.Connection) -> tuple[tuple[str, ...], dict, list]:
    inspector = sa.inspect(connection)
    tables = tuple(sorted(inspector.get_table_names()))
    columns = {
        table: tuple(column["name"] for column in inspector.get_columns(table))
        for table in tables
    }
    rows = connection.execute(sa.text("SELECT id, value FROM sentinel")).all()
    return tables, columns, rows


@pytest.mark.parametrize(("revision", "current_table"), _IRREVERSIBLE_DOWNGRADES)
def test_irreversible_downgrade_fails_before_database_mutation(
    tmp_path: Path, revision: str, current_table: str
) -> None:
    """A rejected downgrade leaves the already-upgraded database untouched."""
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'migration.db'}")
    try:
        with engine.begin() as connection:
            connection.execute(
                sa.text("CREATE TABLE sentinel (id INTEGER PRIMARY KEY, value TEXT)")
            )
            connection.execute(sa.text("INSERT INTO sentinel VALUES (1, 'keep')"))
            if current_table not in {
                "tts_settings",
                "splitter_settings",
                "window_settings",
                "tabs",
            }:
                connection.execute(
                    sa.text(f'CREATE TABLE "{current_table}" (id INTEGER PRIMARY KEY)')
                )
        module = importlib.import_module(
            f"airunner_services.database.alembic.versions.{revision}"
        )
        with engine.connect() as connection:
            before = _snapshot(connection)
            operations = MigrationContext.configure(connection)
            with Operations.context(operations):
                with pytest.raises(
                    RuntimeError,
                    match="Restore a pre-upgrade database backup",
                ):
                    module.downgrade()
            assert _snapshot(connection) == before
    finally:
        engine.dispose()


def test_current_conversation_migration_downgrade_rejects_before_mutation(
    tmp_path: Path,
) -> None:
    """The lossy current_chatbot rollback must preserve the upgraded row."""
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'current-chatbot.db'}")
    migration = importlib.import_module(
        "airunner_services.database.alembic.versions."
        "201952ffe80a_remove_current_conversation_from_llm_"
    )
    try:
        with engine.begin() as connection:
            connection.execute(
                sa.text("CREATE TABLE sentinel (id INTEGER PRIMARY KEY, value TEXT)")
            )
            connection.execute(sa.text("INSERT INTO sentinel VALUES (1, 'keep')"))
            connection.execute(
                sa.text(
                    "CREATE TABLE llm_generator_settings ("
                    "id INTEGER PRIMARY KEY, current_chatbot INTEGER)"
                )
            )
            connection.execute(
                sa.text(
                    "INSERT INTO llm_generator_settings VALUES (1, 73)"
                )
            )

        with engine.connect() as connection:
            before = _snapshot(connection)
            chatbot_values_before = connection.execute(
                sa.text(
                    "SELECT id, current_chatbot FROM llm_generator_settings"
                )
            ).all()
            operations = MigrationContext.configure(connection)
            with Operations.context(operations):
                with pytest.raises(RuntimeError, match="current_conversation values"):
                    migration.downgrade()
            assert _snapshot(connection) == before
            assert connection.execute(
                sa.text(
                    "SELECT id, current_chatbot FROM llm_generator_settings"
                )
            ).all() == chatbot_values_before == [(1, 73)]
    finally:
        engine.dispose()


def test_current_conversation_migration_upgrade_rejects_unmapped_values(
    tmp_path: Path,
) -> None:
    """The migration refuses before dropping a persisted conversation ID."""
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'current-conversation.db'}")
    migration = importlib.import_module(
        "airunner_services.database.alembic.versions."
        "201952ffe80a_remove_current_conversation_from_llm_"
    )
    try:
        with engine.begin() as connection:
            connection.execute(
                sa.text("CREATE TABLE sentinel (id INTEGER PRIMARY KEY, value TEXT)")
            )
            connection.execute(sa.text("INSERT INTO sentinel VALUES (1, 'keep')"))
            connection.execute(
                sa.text(
                    "CREATE TABLE llm_generator_settings ("
                    "id INTEGER PRIMARY KEY, current_conversation INTEGER)"
                )
            )
            connection.execute(
                sa.text(
                    "INSERT INTO llm_generator_settings VALUES (1, 41)"
                )
            )

        with engine.connect() as connection:
            before = _snapshot(connection)
            operations = MigrationContext.configure(connection)
            with Operations.context(operations):
                with pytest.raises(RuntimeError, match="would be discarded"):
                    migration.upgrade()
            assert _snapshot(connection) == before
            assert connection.execute(
                sa.text(
                    "SELECT id, current_conversation FROM llm_generator_settings"
                )
            ).all() == [(1, 41)]
    finally:
        engine.dispose()


def test_current_conversation_migration_allows_nulls_and_preserves_rows(
    tmp_path: Path,
) -> None:
    """Null legacy pointers can be removed while unrelated settings survive."""
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'current-conversation-null.db'}")
    migration = importlib.import_module(
        "airunner_services.database.alembic.versions."
        "201952ffe80a_remove_current_conversation_from_llm_"
    )
    try:
        with engine.begin() as connection:
            connection.execute(
                sa.text("CREATE TABLE chatbots (id INTEGER PRIMARY KEY)")
            )
            connection.execute(sa.text("INSERT INTO chatbots VALUES (73)"))
            connection.execute(
                sa.text(
                    "CREATE TABLE llm_generator_settings ("
                    "id INTEGER PRIMARY KEY, current_conversation INTEGER, "
                    "action TEXT)"
                )
            )
            connection.execute(
                sa.text(
                    "INSERT INTO llm_generator_settings "
                    "(id, current_conversation, action) VALUES "
                    "(1, NULL, 'CHAT'), (2, NULL, 'SUMMARIZE')"
                )
            )

        with engine.connect() as connection:
            operations = MigrationContext.configure(connection)
            with Operations.context(operations):
                migration.upgrade()

            columns = {
                column["name"]
                for column in sa.inspect(connection).get_columns(
                    "llm_generator_settings"
                )
            }
            assert "current_conversation" not in columns
            assert "current_chatbot" in columns
            foreign_keys = sa.inspect(connection).get_foreign_keys(
                "llm_generator_settings"
            )
            assert any(
                foreign_key.get("name") == "current_chatbot_fkey"
                and foreign_key.get("constrained_columns") == ["current_chatbot"]
                and foreign_key.get("referred_table") == "chatbots"
                and foreign_key.get("referred_columns") == ["id"]
                for foreign_key in foreign_keys
            )
            assert connection.execute(
                sa.text(
                    "SELECT id, current_chatbot, action "
                    "FROM llm_generator_settings ORDER BY id"
                )
            ).all() == [(1, None, "CHAT"), (2, None, "SUMMARIZE")]
    finally:
        engine.dispose()


def test_current_conversation_migration_is_idempotent_without_legacy_column(
    tmp_path: Path,
) -> None:
    """An absent legacy column does not prevent creating current_chatbot."""
    engine = sa.create_engine(
        f"sqlite:///{tmp_path / 'current-conversation-absent.db'}"
    )
    migration = importlib.import_module(
        "airunner_services.database.alembic.versions."
        "201952ffe80a_remove_current_conversation_from_llm_"
    )
    try:
        with engine.begin() as connection:
            connection.execute(
                sa.text("CREATE TABLE chatbots (id INTEGER PRIMARY KEY)")
            )
            connection.execute(sa.text("INSERT INTO chatbots VALUES (73)"))
            connection.execute(
                sa.text(
                    "CREATE TABLE llm_generator_settings ("
                    "id INTEGER PRIMARY KEY, action TEXT)"
                )
            )
            connection.execute(
                sa.text(
                    "INSERT INTO llm_generator_settings VALUES (1, 'CHAT')"
                )
            )

        with engine.connect() as connection:
            operations = MigrationContext.configure(connection)
            with Operations.context(operations):
                migration.upgrade()
                migration.upgrade()

            columns = {
                column["name"]
                for column in sa.inspect(connection).get_columns(
                    "llm_generator_settings"
                )
            }
            assert "current_conversation" not in columns
            assert "current_chatbot" in columns
            assert connection.execute(
                sa.text(
                    "SELECT id, current_chatbot, action "
                    "FROM llm_generator_settings"
                )
            ).all() == [(1, None, "CHAT")]
            assert sum(
                foreign_key.get("name") == "current_chatbot_fkey"
                for foreign_key in sa.inspect(connection).get_foreign_keys(
                    "llm_generator_settings"
                )
            ) == 1
    finally:
        engine.dispose()


def _create_legacy_openvoice_table(connection: sa.Connection) -> None:
    connection.execute(
        sa.text(
            "CREATE TABLE openvoice_settings ("
            "id INTEGER PRIMARY KEY, language VARCHAR, speed INTEGER, "
            "tone_color VARCHAR, pitch INTEGER, volume INTEGER, voice VARCHAR, "
            "reference_speaker_path VARCHAR)"
        )
    )
    connection.execute(
        sa.text(
            "INSERT INTO openvoice_settings (id, language) "
            "VALUES (1, 'EN'), (2, 'EN')"
        )
    )


def test_expression_migration_preserves_nulls_and_new_orm_defaults(
    tmp_path: Path,
) -> None:
    """Upgrade adds missing columns without backfilling old rows with guesses."""
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'openvoice.db'}")
    try:
        with engine.begin() as connection:
            _create_legacy_openvoice_table(connection)
            connection.execute(sa.text("CREATE TABLE xtts_settings (id INTEGER)"))

        migration = importlib.import_module(
            "airunner_services.database.alembic.versions."
            "2a7206a1ff79_add_expression_parameters_to_openvoice_"
        )
        with engine.connect() as connection:
            operations = MigrationContext.configure(connection)
            with Operations.context(operations):
                migration.upgrade()
            rows = connection.execute(
                sa.text(
                    "SELECT sdp_ratio, noise_scale, noise_scale_w "
                    "FROM openvoice_settings ORDER BY id"
                )
            ).all()
            assert rows == [(None, None, None), (None, None, None)]
            assert "xtts_settings" not in sa.inspect(connection).get_table_names()

        with Session(engine) as session:
            session.add(OpenVoiceSettings())
            session.commit()
        with engine.connect() as connection:
            assert connection.execute(
                sa.text(
                    "SELECT sdp_ratio, noise_scale, noise_scale_w "
                    "FROM openvoice_settings WHERE id = 3"
                )
            ).one() == (50, 80, 90)
    finally:
        engine.dispose()


def test_expression_migration_keeps_existing_partial_values(
    tmp_path: Path,
) -> None:
    """Rerunning against partially migrated data preserves NULL and values."""
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'partial-openvoice.db'}")
    try:
        with engine.begin() as connection:
            connection.execute(
                sa.text(
                    "CREATE TABLE openvoice_settings ("
                    "id INTEGER PRIMARY KEY, language VARCHAR, speed INTEGER, "
                    "tone_color VARCHAR, pitch INTEGER, volume INTEGER, voice VARCHAR, "
                    "reference_speaker_path VARCHAR, sdp_ratio INTEGER, "
                    "noise_scale INTEGER, noise_scale_w INTEGER)"
                )
            )
            connection.execute(
                sa.text(
                    "INSERT INTO openvoice_settings "
                    "(id, sdp_ratio, noise_scale, noise_scale_w) "
                    "VALUES (1, NULL, 47, NULL)"
                )
            )
        migration = importlib.import_module(
            "airunner_services.database.alembic.versions."
            "2a7206a1ff79_add_expression_parameters_to_openvoice_"
        )
        with engine.connect() as connection:
            operations = MigrationContext.configure(connection)
            with Operations.context(operations):
                migration.upgrade()
            assert connection.execute(
                sa.text(
                    "SELECT sdp_ratio, noise_scale, noise_scale_w "
                    "FROM openvoice_settings WHERE id = 1"
                )
            ).one() == (None, 47, None)
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "revision",
    ["5dbbe8800572_add_tabs_table", "c0f6743e26e9_better_splitter_handling"],
)
def test_historical_noop_revision_remains_schema_and_data_neutral(
    tmp_path: Path, revision: str
) -> None:
    """Keep verified no-op history harmless in both migration directions."""
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'noop.db'}")
    try:
        with engine.begin() as connection:
            connection.execute(
                sa.text("CREATE TABLE sentinel (id INTEGER PRIMARY KEY, value TEXT)")
            )
            connection.execute(sa.text("INSERT INTO sentinel VALUES (1, 'keep')"))
        module = importlib.import_module(
            f"airunner_services.database.alembic.versions.{revision}"
        )
        with engine.connect() as connection:
            before = _snapshot(connection)
            operations = MigrationContext.configure(connection)
            with Operations.context(operations):
                module.upgrade()
                module.downgrade()
            assert _snapshot(connection) == before
    finally:
        engine.dispose()
