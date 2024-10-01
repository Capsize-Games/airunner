"""Add tts_model_path to path_settings

Revision ID: f5092c1a90f7
Revises: 7766054d170b
Create Date: 2024-10-01 12:06:21.714869

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = 'f5092c1a90f7'
down_revision: Union[str, None] = '7766054d170b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('path_settings', sa.Column('tts_model_path', sa.String(), nullable=True, server_default='default/path/to/tts_model'))

def downgrade():
    op.drop_column('path_settings', 'tts_model_path')
    # ### end Alembic commands ###
