"""Drop columns from tts_settings

Revision ID: 98be29ddea23
Revises: f5092c1a90f7
Create Date: 2024-10-01 16:26:42.583525

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '98be29ddea23'
down_revision: Union[str, None] = 'f5092c1a90f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Check if the columns exist before attempting to drop them
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('tts_settings')]

    if 'enable_cpu_offload' in columns:
        op.drop_column('tts_settings', 'enable_cpu_offload')
    if 'play_queue_buffer_length' in columns:
        op.drop_column('tts_settings', 'play_queue_buffer_length')

def downgrade():
    # Recreate the columns in case of a downgrade
    op.add_column('tts_settings', sa.Column('enable_cpu_offload', sa.Boolean, default=True))
    op.add_column('tts_settings', sa.Column('play_queue_buffer_length', sa.Integer, default=1))
    # ### end Alembic commands ###
