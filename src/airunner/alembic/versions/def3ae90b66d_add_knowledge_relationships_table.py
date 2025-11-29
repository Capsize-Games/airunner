"""add knowledge relationships table

Revision ID: def3ae90b66d
Revises: 500b6c395d38
Create Date: 2025-10-28 13:23:15.005536

NOTE: This table was later removed in migration f480bbc9acdb.
The model class has been deleted, so this migration is now a no-op.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "def3ae90b66d"
down_revision: Union[str, None] = "500b6c395d38"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Table creation - if it doesn't exist, create it
    # (will be dropped later by migration f480bbc9acdb)
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "knowledge_relationships" not in inspector.get_table_names():
        op.create_table(
            "knowledge_relationships",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("source_fact_id", sa.Integer(), nullable=False),
            sa.Column("target_fact_id", sa.Integer(), nullable=False),
            sa.Column("relationship_type", sa.String(50), nullable=False),
            sa.Column("strength", sa.Float(), default=1.0),
            sa.Column("created_at", sa.DateTime()),
        )


def downgrade() -> None:
    # Drop if exists
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "knowledge_relationships" in inspector.get_table_names():
        op.drop_table("knowledge_relationships")
