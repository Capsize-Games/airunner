"""add_model_version_column_to_schedulers

Revision ID: add_model_version_schedulers
Revises: d2ab5f1c9a7e
Create Date: 2026-06-06 23:58:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "add_model_version_schedulers"
down_revision: Union[str, None] = "d2ab5f1c9a7e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add model_version column to schedulers table (idempotent)."""
    from sqlalchemy import inspect  # noqa: PLC0415

    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("schedulers")]
    if "model_version" not in columns:
        op.add_column(
            "schedulers",
            sa.Column("model_version", sa.String(), nullable=True),
        )


def downgrade() -> None:
    """Remove model_version column from schedulers table."""
    op.drop_column("schedulers", "model_version")
