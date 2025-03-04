"""Add use_grid_image_as_input and lock_input_image to OutpaintSettings

Revision ID: 713878b6e38f
Revises: 75020956e3e2
Create Date: 2025-02-04 18:52:23.277083

"""
from typing import Sequence, Union

from sqlalchemy.engine.reflection import Inspector
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '713878b6e38f'
down_revision: Union[str, None] = '75020956e3e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    columns_outpaint_settings = [col['name'] for col in inspector.get_columns('outpaint_settings')]

    try:
        with op.batch_alter_table('outpaint_settings') as batch_op:
            if 'use_grid_image_as_input' not in columns_outpaint_settings:
                batch_op.add_column(sa.Column('use_grid_image_as_input', sa.Boolean(), nullable=True))
            else:
                print("Column 'use_grid_image_as_input' already exists, skipping add.")

            if 'lock_input_image' not in columns_outpaint_settings:
                batch_op.add_column(sa.Column('lock_input_image', sa.Boolean(), nullable=True))
            else:
                print("Column 'lock_input_image' already exists, skipping add.")
    except Exception as e:
        print("Error adding columns: ", e)

def downgrade() -> None:
    try:
        with op.batch_alter_table('outpaint_settings') as batch_op:
            batch_op.drop_column('use_grid_image_as_input')
            batch_op.drop_column('lock_input_image')
    except Exception as e:
        print("Error dropping columns: ", e)
