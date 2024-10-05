"""add controlnet_enabled column to application_settings table

Revision ID: f4d8b6e9a1e8
Revises: 8ebcece37db8
Create Date: 2024-10-04 16:03:50.609825

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = 'f4d8b6e9a1e8'
down_revision: Union[str, None] = '8ebcece37db8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('application_settings', sa.Column('controlnet_enabled', sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column('application_settings', 'controlnet_enabled')
    # ### end Alembic commands ###
