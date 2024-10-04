"""Add lora_scale to generator_settings

Revision ID: 8ebcece37db8
Revises: 4626ae0d0601
Create Date: 2024-10-04 10:16:43.172811

"""
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
    op.add_column('generator_settings', sa.Column('lora_scale', sa.Integer, default=100))

def downgrade():
    op.drop_column('generator_settings', 'lora_scale')
    # ### end Alembic commands ###
