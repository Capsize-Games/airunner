"""add_conversation_summary_settings

Revision ID: add_conversation_summary_settings
Revises: add_provider_api_base_url
Create Date: 2026-06-08 00:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "add_conversation_summary_settings"
down_revision: Union[str, None] = "add_provider_api_base_url"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add summarization settings to llm_generator_settings (idempotent)."""
    from sqlalchemy import inspect  # noqa: PLC0415

    conn = op.get_bind()
    inspector = inspect(conn)
    columns = {
        c["name"] for c in inspector.get_columns("llm_generator_settings")
    }

    if "perform_conversation_summary" not in columns:
        op.add_column(
            "llm_generator_settings",
            sa.Column(
                "perform_conversation_summary",
                sa.Boolean(),
                nullable=False,
                server_default=sa.sql.expression.false(),
            ),
        )

    if "summarize_after_n_turns" not in columns:
        op.add_column(
            "llm_generator_settings",
            sa.Column(
                "summarize_after_n_turns",
                sa.Integer(),
                nullable=False,
                server_default="8",
            ),
        )


def downgrade() -> None:
    """Remove summarization settings from llm_generator_settings."""
    op.drop_column("llm_generator_settings", "summarize_after_n_turns")
    op.drop_column("llm_generator_settings", "perform_conversation_summary")
