"""move client-local language and audio settings to QSettings

Revision ID: d2ab5f1c9a7e
Revises: 48b1c0d3e4f5, 5a4d9d9e0b67, b1c4d5e6f7a8
Create Date: 2026-05-15 00:00:00.000000

"""

from __future__ import annotations

import configparser
import os
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from airunner_services.settings import AIRUNNER_BASE_PATH

revision: str = "d2ab5f1c9a7e"
down_revision: Union[tuple[str, ...], None] = (
    "48b1c0d3e4f5",
    "5a4d9d9e0b67",
    "b1c4d5e6f7a8",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Move GUI-local settings out of shared database tables."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    _migrate_gui_language(bind, inspector)
    _migrate_audio_device(bind, inspector, "playback_device")
    _migrate_audio_device(bind, inspector, "recording_device")
    _drop_column_if_present(inspector, "language_settings", "gui_language")
    _drop_column_if_present(inspector, "sound_settings", "playback_device")
    _drop_column_if_present(inspector, "sound_settings", "recording_device")


def downgrade() -> None:
    """Client-local settings are not restored to shared DB tables."""
    return None


def _migrate_gui_language(bind, inspector) -> None:
    """Copy one persisted GUI language value into QSettings."""
    if not _has_column(inspector, "language_settings", "gui_language"):
        return
    row = (
        bind.execute(
            sa.text(
                "SELECT gui_language FROM language_settings "
                "ORDER BY id LIMIT 1"
            )
        )
        .mappings()
        .first()
    )
    if row is None:
        return
    value = row.get("gui_language")
    if value:
        _write_qsettings_value("language", "gui_language", str(value))


def _migrate_audio_device(bind, inspector, column_name: str) -> None:
    """Copy one persisted audio device selection into QSettings."""
    if not _has_column(inspector, "sound_settings", column_name):
        return
    row = (
        bind.execute(
            sa.text(
                f"SELECT {column_name} FROM sound_settings ORDER BY id LIMIT 1"
            )
        )
        .mappings()
        .first()
    )
    if row is None:
        return
    value = row.get(column_name)
    if value:
        _write_qsettings_value("audio_devices", column_name, str(value))


def _write_qsettings_value(section: str, key: str, value: str) -> None:
    """Persist one migrated value into AIRunner's shared settings.ini."""
    config_path = os.path.join(
        os.path.expanduser(AIRUNNER_BASE_PATH),
        "config",
        "settings.ini",
    )
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    parser = configparser.ConfigParser()
    if os.path.exists(config_path):
        parser.read(config_path)
    if not parser.has_section(section):
        parser.add_section(section)
    parser.set(section, key, value)
    with open(config_path, "w", encoding="utf-8") as handle:
        parser.write(handle)


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    """Return whether one table still includes one named column."""
    if not inspector.has_table(table_name):
        return False
    existing = {column["name"] for column in inspector.get_columns(table_name)}
    return column_name in existing


def _drop_column_if_present(
    inspector,
    table_name: str,
    column_name: str,
) -> None:
    """Drop one named column when the target table still has it."""
    if not _has_column(inspector, table_name, column_name):
        return
    recreate = "always" if op.get_bind().dialect.name == "sqlite" else "auto"
    with op.batch_alter_table(table_name, recreate=recreate) as batch_op:
        batch_op.drop_column(column_name)
