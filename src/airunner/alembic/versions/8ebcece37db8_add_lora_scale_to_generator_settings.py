from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '8ebcece37db8'
down_revision: Union[str, None] = '4626ae0d0601'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    # Check if the 'lora_scale' column already exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [column['name'] for column in inspector.get_columns('generator_settings')]

    if 'lora_scale' not in columns:
        op.add_column('generator_settings', sa.Column('lora_scale', sa.Integer, default=100))

def downgrade():
    # Drop the 'lora_scale' column if it exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [column['name'] for column in inspector.get_columns('generator_settings')]

    if 'lora_scale' in columns:
        op.drop_column('generator_settings', 'lora_scale')
    # ### end Alembic commands ###
