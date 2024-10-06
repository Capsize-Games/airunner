"""Add x_pos and y_pos to drawing_pad_settings

Revision ID: e8acc6604a78
Revises: caf014343bfa
Create Date: 2024-10-05 14:34:54.869392

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = 'e8acc6604a78'
down_revision: Union[str, None] = 'caf014343bfa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Check if the columns already exist before adding them
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('drawing_pad_settings')]

    if 'x_pos' not in columns:
        op.add_column('drawing_pad_settings', sa.Column('x_pos', sa.Integer(), default=0))

    if 'y_pos' not in columns:
        op.add_column('drawing_pad_settings', sa.Column('y_pos', sa.Integer(), default=0))

def downgrade():
    # Drop the columns if they exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('drawing_pad_settings')]

    if 'x_pos' in columns:
        op.drop_column('drawing_pad_settings', 'x_pos')

    if 'y_pos' in columns:
        op.drop_column('drawing_pad_settings', 'y_pos')
    # ### end Alembic commands ###
