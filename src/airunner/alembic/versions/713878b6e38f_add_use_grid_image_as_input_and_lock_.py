"""Add use_grid_image_as_input and lock_input_image to OutpaintSettings

Revision ID: 713878b6e38f
Revises: 75020956e3e2
Create Date: 2025-02-04 18:52:23.277083

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '713878b6e38f'
down_revision: Union[str, None] = '75020956e3e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    try:
        with op.batch_alter_table('outpaint_settings') as batch_op:
            batch_op.add_column(sa.Column('use_grid_image_as_input', sa.Boolean(), nullable=True))
            batch_op.add_column(sa.Column('lock_input_image', sa.Boolean(), nullable=True))
    except sqlite.DatabaseError:
        pass



def downgrade() -> None:
    try:
        with op.batch_alter_table('outpaint_settings') as batch_op:
            batch_op.drop_column('use_grid_image_as_input')
            batch_op.drop_column('lock_input_image')
    except sqlite.DatabaseError:
        pass
