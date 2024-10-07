"""Add mask_layer_enabled to drawing_pad_settings

Revision ID: 890ad8ef1c73
Revises: 7f11862f91a3
Create Date: 2024-10-07 10:59:56.816282

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '890ad8ef1c73'
down_revision: Union[str, None] = '7f11862f91a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Check if the column exists before adding it
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('drawing_pad_settings')]

    if 'mask_layer_enabled' not in columns:
        op.add_column('drawing_pad_settings', sa.Column('mask_layer_enabled', sa.Boolean, default=False))

def downgrade():
    # Drop the column if it exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('drawing_pad_settings')]

    if 'mask_layer_enabled' in columns:
        op.drop_column('drawing_pad_settings', 'mask_layer_enabled')
    # ### end Alembic commands ###
