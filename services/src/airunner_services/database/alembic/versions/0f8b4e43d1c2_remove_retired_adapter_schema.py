"""remove retired adapter schema

Revision ID: 0f8b4e43d1c2
Revises: 6b0f0f6c3e4a
Create Date: 2026-05-17 00:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0f8b4e43d1c2"
down_revision: Union[str, None] = "6b0f0f6c3e4a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop retired adapter, LoRA, and embedding schema."""
    inspector = sa.inspect(op.get_bind())
    _drop_column_if_present(
        inspector,
        "llm_generator_settings",
        "enabled_adapters",
    )
    _drop_column_if_present(
        inspector,
        "generator_settings",
        "lora_scale",
    )
    _drop_column_if_present(
        inspector,
        "metadata_settings",
        "image_export_metadata_lora",
    )
    _drop_column_if_present(
        inspector,
        "metadata_settings",
        "image_export_metadata_embeddings",
    )
    _drop_table_if_present(inspector, "lora")
    _drop_table_if_present(inspector, "embeddings")
    _drop_table_if_present(inspector, "fine_tuned_models")


def downgrade() -> None:
    """Retired schema is not restored on downgrade."""
    return None


def _has_column(
    inspector,
    table_name: str,
    column_name: str,
) -> bool:
    """Return whether the named table still includes the column."""
    if not inspector.has_table(table_name):
        return False
    existing = {
        column["name"] for column in inspector.get_columns(table_name)
    }
    return column_name in existing


def _drop_column_if_present(
    inspector,
    table_name: str,
    column_name: str,
) -> None:
    """Drop one named column when it still exists."""
    if not _has_column(inspector, table_name, column_name):
        return
    recreate = "always" if op.get_bind().dialect.name == "sqlite" else "auto"
    with op.batch_alter_table(table_name, recreate=recreate) as batch_op:
        batch_op.drop_column(column_name)


def _drop_table_if_present(inspector, table_name: str) -> None:
    """Drop one named table when it still exists."""
    if inspector.has_table(table_name):
        op.drop_table(table_name)