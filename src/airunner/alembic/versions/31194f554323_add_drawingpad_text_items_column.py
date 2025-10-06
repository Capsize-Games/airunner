"""add drawingpad text items column

Revision ID: 31194f554323
Revises: 6b36790f3292
Create Date: 2025-09-30 12:52:13.557739

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "31194f554323"
down_revision: Union[str, None] = "6b36790f3292"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Add a nullable text_items column to drawing_pad_settings
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    try:
        existing_cols = [
            c["name"] for c in inspector.get_columns("drawing_pad_settings")
        ]
    except Exception:
        existing_cols = []

    if "text_items" in existing_cols:
        # Column already exists; nothing to do
        return

    with op.batch_alter_table(
        "drawing_pad_settings", recreate="auto"
    ) as batch_op:
        batch_op.add_column(sa.Column("text_items", sa.Text(), nullable=True))


def downgrade():
    # Remove the text_items column if present
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    try:
        existing_cols = [
            c["name"] for c in inspector.get_columns("drawing_pad_settings")
        ]
    except Exception:
        existing_cols = []

    if "text_items" not in existing_cols:
        return

    with op.batch_alter_table(
        "drawing_pad_settings", recreate="auto"
    ) as batch_op:
        try:
            batch_op.drop_column("text_items")
        except Exception:
            # If drop not supported on this DB, ignore
            pass
