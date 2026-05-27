"""move client-local application settings to QSettings

Revision ID: 6b0f0f6c3e4a
Revises: d2ab5f1c9a7e
Create Date: 2026-05-15 00:30:00.000000

"""

from __future__ import annotations

import configparser
import os
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from airunner_model.settings import AIRUNNER_BASE_PATH


revision: str = "6b0f0f6c3e4a"
down_revision: Union[str, tuple[str, ...], None] = "d2ab5f1c9a7e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_CLIENT_LOCAL_APPLICATION_SETTINGS = {
    "active_grid_size_lock": "application_settings",
    "age_agreement_checked": "application_settings",
    "airunner_agreement_checked": "application_settings",
    "current_layer_index": "application_settings",
    "current_tool": "application_settings",
    "dark_mode_enabled": "application_settings",
    "download_wizard_completed": "application_settings",
    "generator_section": "application_settings",
    "image_to_new_layer": "application_settings",
    "is_maximized": "window_settings",
    "latest_version_check": "application_settings",
    "llama_license_agreement_checked": "application_settings",
    "override_system_theme": "application_settings",
    "paths_initialized": "application_settings",
    "pivot_point_x": "application_settings",
    "pivot_point_y": "application_settings",
    "resize_on_paste": "application_settings",
    "run_setup_wizard": "application_settings",
    "show_active_image_area": "application_settings",
    "stable_diffusion_agreement_checked": "application_settings",
    "user_agreement_checked": "application_settings",
}
_NULLABLE_APPLICATION_SETTING_COLUMNS = {"current_tool"}


def upgrade() -> None:
    """Move GUI-local application settings out of the shared database."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for column_name, section in _CLIENT_LOCAL_APPLICATION_SETTINGS.items():
        _migrate_application_setting(
            bind,
            inspector,
            column_name,
            section,
            nullable=column_name in _NULLABLE_APPLICATION_SETTING_COLUMNS,
        )
    _drop_columns_if_present(
        inspector,
        "application_settings",
        tuple(_CLIENT_LOCAL_APPLICATION_SETTINGS),
    )


def downgrade() -> None:
    """Client-local application settings are not restored to SQLite."""
    return None


def _migrate_application_setting(
    bind,
    inspector,
    column_name: str,
    section: str,
    *,
    nullable: bool = False,
) -> None:
    """Copy one persisted application setting value into QSettings."""
    if not _has_column(inspector, "application_settings", column_name):
        return
    row = bind.execute(
        sa.text(
            f"SELECT {column_name} FROM application_settings "
            "ORDER BY id LIMIT 1"
        )
    ).mappings().first()
    if row is None:
        return
    value = row.get(column_name)
    if value is None and not nullable:
        return
    _write_qsettings_value(
        section,
        column_name,
        _serialize_qsettings_value(value),
    )


def _serialize_qsettings_value(value) -> str:
    """Serialize one migrated application setting for settings.ini."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


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
    existing = {
        column["name"] for column in inspector.get_columns(table_name)
    }
    return column_name in existing


def _drop_columns_if_present(
    inspector,
    table_name: str,
    column_names: Sequence[str],
) -> None:
    """Drop each named column when the target table still has it."""
    existing = [
        column_name
        for column_name in column_names
        if _has_column(inspector, table_name, column_name)
    ]
    if not existing:
        return
    recreate = "always" if op.get_bind().dialect.name == "sqlite" else "auto"
    with op.batch_alter_table(table_name, recreate=recreate) as batch_op:
        for column_name in existing:
            batch_op.drop_column(column_name)