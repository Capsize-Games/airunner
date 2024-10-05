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
    # Check if the 'tts_model_path' column already exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [column['name'] for column in inspector.get_columns('path_settings')]

    if 'tts_model_path' not in columns:
        op.add_column('path_settings', sa.Column('tts_model_path', sa.String(), nullable=True, server_default='default/path/to/tts_model'))

def downgrade():
    # Drop the 'tts_model_path' column if it exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [column['name'] for column in inspector.get_columns('path_settings')]

    if 'tts_model_path' in columns:
        op.drop_column('path_settings', 'tts_model_path')
    # ### end Alembic commands ###
