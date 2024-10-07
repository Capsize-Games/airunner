"""Add strength and mask_blur to outpaint_settings

Revision ID: 7f11862f91a3
Revises: 0fc917cc342e
Create Date: 2024-10-07 10:35:14.413298

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '7f11862f91a3'
down_revision: Union[str, None] = '0fc917cc342e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Check if the columns exist before adding them
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('outpaint_settings')]

    if 'strength' not in columns:
        op.add_column('outpaint_settings', sa.Column('strength', sa.Integer, default=50))

    if 'mask_blur' not in columns:
        op.add_column('outpaint_settings', sa.Column('mask_blur', sa.Integer, default=0))

def downgrade():
    # Drop the columns if they exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('outpaint_settings')]

    if 'strength' in columns:
        op.drop_column('outpaint_settings', 'strength')

    if 'mask_blur' in columns:
        op.drop_column('outpaint_settings', 'mask_blur')
    # ### end Alembic commands ###
