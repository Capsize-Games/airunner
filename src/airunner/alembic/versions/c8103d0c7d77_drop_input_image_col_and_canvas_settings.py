"""drop input_image col and canvas_settings

Revision ID: c8103d0c7d77
Revises: e8acc6604a78
Create Date: 2024-10-05 20:18:49.170629

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = 'c8103d0c7d77'
down_revision: Union[str, None] = 'e8acc6604a78'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Reflect the generator_settings table
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('generator_settings')]

    # Remove the input_image column from generator_settings if it exists
    if 'input_image' in columns:
        with op.batch_alter_table('generator_settings') as batch_op:
            batch_op.drop_column('input_image')

    # Drop the canvas_settings table if it exists
    if inspector.has_table('canvas_settings'):
        op.drop_table('canvas_settings')

def downgrade():
    # Add the input_image column back to generator_settings
    with op.batch_alter_table('generator_settings') as batch_op:
        batch_op.add_column(sa.Column('input_image', sa.String, nullable=True))

    # Recreate the canvas_settings table
    op.create_table(
        'canvas_settings',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        # Add other columns as necessary
    )
    # ### end Alembic commands ###
