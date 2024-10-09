"""Add lock_input_image column to image_to_image_settings

Revision ID: 6d58cbfd61fb
Revises: 72d9134823cb
Create Date: 2024-10-09 10:05:11.349862

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

from airunner.utils.db.column_exists import column_exists

# revision identifiers, used by Alembic.
revision: str = '6d58cbfd61fb'
down_revision: Union[str, None] = '72d9134823cb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    if not column_exists('image_to_image_settings', 'lock_input_image'):
        op.add_column('image_to_image_settings', sa.Column('lock_input_image', sa.Boolean, default=False))
    if not column_exists('controlnet_settings', 'lock_input_image'):
        op.add_column('controlnet_settings', sa.Column('lock_input_image', sa.Boolean, default=False))

def downgrade():
    if column_exists('image_to_image_settings', 'lock_input_image'):
        op.drop_column('image_to_image_settings', 'lock_input_image')
    if column_exists('controlnet_settings', 'lock_input_image'):
        op.drop_column('image_to_image_settings', 'lock_input_image')
    # ### end Alembic commands ###
