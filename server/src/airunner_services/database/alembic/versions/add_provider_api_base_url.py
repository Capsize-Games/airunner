"""add_api_base_url_to_llm_generator_settings

Revision ID: add_provider_api_base_url
Revises: add_model_version_schedulers
Create Date: 2026-06-08 00:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "add_provider_api_base_url"
down_revision: Union[str, None] = "add_model_version_schedulers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add api_base_url column to llm_generator_settings (idempotent)."""
    from sqlalchemy import inspect  # noqa: PLC0415

    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("llm_generator_settings")]
    if "api_base_url" not in columns:
        op.add_column(
            "llm_generator_settings",
            sa.Column("api_base_url", sa.String(), nullable=True),
        )


def downgrade() -> None:
    """Remove api_base_url column from llm_generator_settings."""
    op.drop_column("llm_generator_settings", "api_base_url")
