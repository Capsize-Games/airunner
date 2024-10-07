"""Conditionally add metadata columns to metadata_settings

Revision ID: 0fc917cc342e
Revises: af662d0dcfe0
Create Date: 2024-10-07 07:23:56.129961

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '0fc917cc342e'
down_revision: Union[str, None] = 'af662d0dcfe0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('metadata_settings')]

    if 'image_export_metadata_strength' not in columns:
        op.add_column('metadata_settings', sa.Column('image_export_metadata_strength', sa.Boolean, default=True))
    if 'image_export_metadata_clip_skip' not in columns:
        op.add_column('metadata_settings', sa.Column('image_export_metadata_clip_skip', sa.Boolean, default=True))
    if 'image_export_metadata_version' not in columns:
        op.add_column('metadata_settings', sa.Column('image_export_metadata_version', sa.Boolean, default=True))
    if 'image_export_metadata_lora' not in columns:
        op.add_column('metadata_settings', sa.Column('image_export_metadata_lora', sa.Boolean, default=True))
    if 'image_export_metadata_embeddings' not in columns:
        op.add_column('metadata_settings', sa.Column('image_export_metadata_embeddings', sa.Boolean, default=True))
    if 'image_export_metadata_timestamp' not in columns:
        op.add_column('metadata_settings', sa.Column('image_export_metadata_timestamp', sa.Boolean, default=True))
    if 'image_export_metadata_controlnet' not in columns:
        op.add_column('metadata_settings', sa.Column('image_export_metadata_controlnet', sa.Boolean, default=True))

def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('metadata_settings')]

    if 'image_export_metadata_prompt_2' in columns:
        op.drop_column('metadata_settings', 'image_export_metadata_prompt_2')
    if 'image_export_metadata_negative_prompt_2' in columns:
        op.drop_column('metadata_settings', 'image_export_metadata_negative_prompt_2')
    if 'image_export_metadata_strength' in columns:
        op.drop_column('metadata_settings', 'image_export_metadata_strength')
    if 'image_export_metadata_clip_skip' in columns:
        op.drop_column('metadata_settings', 'image_export_metadata_clip_skip')
    if 'image_export_metadata_version' in columns:
        op.drop_column('metadata_settings', 'image_export_metadata_version')
    if 'image_export_metadata_lora' in columns:
        op.drop_column('metadata_settings', 'image_export_metadata_lora')
    if 'image_export_metadata_embeddings' in columns:
        op.drop_column('metadata_settings', 'image_export_metadata_embeddings')
    if 'image_export_metadata_timestamp' in columns:
        op.drop_column('metadata_settings', 'image_export_metadata_timestamp')
    if 'image_export_metadata_controlnet' in columns:
        op.drop_column('metadata_settings', 'image_export_metadata_controlnet')
    # ### end Alembic commands ###
