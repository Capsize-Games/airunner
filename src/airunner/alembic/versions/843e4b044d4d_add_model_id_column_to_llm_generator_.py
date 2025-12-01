"""add model_id column to llm_generator_settings

Revision ID: 843e4b044d4d
Revises: f480bbc9acdb
Create Date: 2025-11-30 17:05:07.287217

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from airunner.utils.db.engine import get_inspector


# revision identifiers, used by Alembic.
revision: str = '843e4b044d4d'
down_revision: Union[str, None] = 'f480bbc9acdb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if column already exists
    inspector = get_inspector()
    columns = [col["name"] for col in inspector.get_columns("llm_generator_settings")]
    if "model_id" not in columns:
        op.add_column(
            'llm_generator_settings',
            sa.Column('model_id', sa.String(), nullable=True)
        )


def downgrade() -> None:
    # SQLite doesn't support DROP COLUMN easily, so we skip it
    pass