"""convert lora scale column to integer

Revision ID: 4626ae0d0601
Revises: 7e744b48e075
Create Date: 2024-10-04 08:04:43.962151

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite
from sqlalchemy.sql import table, column

# revision identifiers, used by Alembic.
revision: str = '4626ae0d0601'
down_revision: Union[str, None] = '7e744b48e075'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Check if the scale_temp column already exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('lora')]

    if 'scale_temp' not in columns:
        # Create a temporary column to store the integer values
        op.add_column('lora', sa.Column('scale_temp', sa.Integer(), nullable=True))

    # Convert existing float values to integers and store them in the temporary column
    lora_table = table('lora', column('scale', sa.Float), column('scale_temp', sa.Integer))
    op.execute(
        lora_table.update().values(
            scale_temp=(lora_table.c.scale * 100).cast(sa.Integer)
        )
    )

    # Create a new table with the desired schema
    op.create_table(
        'lora_new',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('scale', sa.Integer, nullable=False),
        sa.Column('enabled', sa.Boolean, nullable=False),
        sa.Column('loaded', sa.Boolean, default=False, nullable=False),
        sa.Column('trigger_word', sa.String, nullable=True),
        sa.Column('path', sa.String, nullable=True),
        sa.Column('version', sa.String, nullable=True)
    )

    # Copy data from the old table to the new table
    op.execute(
        'INSERT INTO lora_new (id, name, scale, enabled, loaded, trigger_word, path, version) '
        'SELECT id, name, scale_temp, enabled, loaded, trigger_word, path, version FROM lora'
    )

    # Drop the old table
    op.drop_table('lora')

    # Rename the new table to the original table name
    op.rename_table('lora_new', 'lora')


def downgrade():
    # Check if the scale_temp column already exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('lora')]

    if 'scale_temp' not in columns:
        # Create a temporary column to store the float values
        op.add_column('lora', sa.Column('scale_temp', sa.Float(), nullable=True))

    # Convert existing integer values to floats and store them in the temporary column
    lora_table = table('lora', column('scale', sa.Integer), column('scale_temp', sa.Float))
    op.execute(
        lora_table.update().values(
            scale_temp=(lora_table.c.scale / 100).cast(sa.Float)
        )
    )

    # Create a new table with the desired schema
    op.create_table(
        'lora_new',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('scale', sa.Float, nullable=False),
        sa.Column('enabled', sa.Boolean, nullable=False),
        sa.Column('loaded', sa.Boolean, default=False, nullable=False),
        sa.Column('trigger_word', sa.String, nullable=True),
        sa.Column('path', sa.String, nullable=True),
        sa.Column('version', sa.String, nullable=True)
    )

    # Copy data from the old table to the new table
    op.execute(
        'INSERT INTO lora_new (id, name, scale, enabled, loaded, trigger_word, path, version) '
        'SELECT id, name, scale_temp, enabled, loaded, trigger_word, path, version FROM lora'
    )

    # Drop the old table
    op.drop_table('lora')

    # Rename the new table to the original table name
    op.rename_table('lora_new', 'lora')
