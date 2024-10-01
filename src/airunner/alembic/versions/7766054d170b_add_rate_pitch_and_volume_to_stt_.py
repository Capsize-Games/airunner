"""Add rate, pitch, and volume to stt_settings

Revision ID: 7766054d170b
Revises: 4c51e062edc4
Create Date: 2024-10-01 07:06:32.076662

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '7766054d170b'
down_revision: Union[str, None] = '4c51e062edc4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    try:
        op.add_column('speech_t5_settings', sa.Column('rate', sa.Integer(), nullable=True, default=100))
        op.add_column('speech_t5_settings', sa.Column('pitch', sa.Integer(), nullable=True, default=100))
        op.add_column('speech_t5_settings', sa.Column('volume', sa.Integer(), nullable=True, default=100))
    except Exception as e:
        pass

def downgrade():
    op.drop_column('speech_t5_settings', 'rate')
    op.drop_column('speech_t5_settings', 'pitch')
    op.drop_column('speech_t5_settings', 'volume')
    # ### end Alembic commands ###
