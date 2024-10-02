"""Drop keyboard_shortcuts table if it exists

Revision ID: a19af7bc4d12
Revises: 2d50ba1fd8ca
Create Date: 2024-10-02 09:41:41.755226

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = 'a19af7bc4d12'
down_revision: Union[str, None] = '2d50ba1fd8ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Drop the keyboard_shortcuts table if it exists
    op.execute('DROP TABLE IF EXISTS keyboard_shortcuts')

def downgrade():
    # Recreate the keyboard_shortcuts table in case of downgrade
    op.create_table(
        'keyboard_shortcuts',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('display_name', sa.String, nullable=False),
        sa.Column('text', sa.String, nullable=False),
        sa.Column('key', sa.Integer, nullable=False),
        sa.Column('modifiers', sa.Integer, nullable=False),
        sa.Column('description', sa.String, nullable=False),
        sa.Column('signal', sa.Integer, nullable=False)
    )
    # ### end Alembic commands ###
