"""Modify columns in stt_settings table

Revision ID: 3212e8fccc68
Revises: 6d58cbfd61fb
Create Date: 2024-10-13 09:29:29.878635

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '3212e8fccc68'
down_revision: Union[str, None] = '6d58cbfd61fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    # Modify columns to Float if they are not already Float
    try:
        with op.batch_alter_table('stt_settings') as batch_op:
            batch_op.alter_column('volume_input_threshold', type_=sa.Float, existing_type=sa.Integer)
            batch_op.alter_column('silence_buffer_seconds', type_=sa.Float, existing_type=sa.Integer)
            batch_op.alter_column('chunk_duration', type_=sa.Float, existing_type=sa.Integer)
    except sqlite.DatabaseError:
        pass

def downgrade():
    # Revert columns back to Integer
    try:
        with op.batch_alter_table('stt_settings') as batch_op:
            batch_op.alter_column('volume_input_threshold', type_=sa.Integer, existing_type=sa.Float)
            batch_op.alter_column('silence_buffer_seconds', type_=sa.Integer, existing_type=sa.Float)
            batch_op.alter_column('chunk_duration', type_=sa.Integer, existing_type=sa.Float)
    except sqlite.DatabaseError:
        pass
    # ### end Alembic commands ###
