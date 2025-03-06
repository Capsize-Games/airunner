"""Change image and mask columns to BLOB

Revision ID: 26a0d29a3af3
Revises: f403ff7468e8
Create Date: 2024-10-24 12:31:37.706170

"""
from typing import Union

import sqlalchemy as sa
from airunner.utils.db import safe_alter_column

revision: str = '26a0d29a3af3'
down_revision: Union[str, None] = 'f403ff7468e8'


def upgrade():
    safe_alter_column('controlnet_settings', 'image', sa.LargeBinary, sa.String, nullable=True)
    safe_alter_column('controlnet_settings', 'generated_image', sa.LargeBinary, sa.String, nullable=True)
    safe_alter_column('image_to_image_settings', 'image', sa.LargeBinary, sa.String, nullable=True)
    safe_alter_column('outpaint_settings', 'image', sa.LargeBinary, sa.String, nullable=True)
    safe_alter_column('drawing_pad_settings', 'image', sa.LargeBinary, sa.String, nullable=True)
    safe_alter_column('drawing_pad_settings', 'mask', sa.LargeBinary, sa.String, nullable=True)

def downgrade():
    safe_alter_column('controlnet_settings', 'image', sa.String, sa.LargeBinary, nullable=True)
    safe_alter_column('controlnet_settings', 'generated_image', sa.String, sa.LargeBinary, nullable=True)
    safe_alter_column('image_to_image_settings', 'image', sa.String, sa.LargeBinary, nullable=True)
    safe_alter_column('outpaint_settings', 'image', sa.String, sa.LargeBinary, nullable=True)
    safe_alter_column('drawing_pad_settings', 'image', sa.String, sa.LargeBinary, nullable=True)
    safe_alter_column('drawing_pad_settings', 'mask', sa.String, sa.LargeBinary, nullable=True)
