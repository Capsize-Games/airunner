"""Change image and mask columns to BLOB

Revision ID: 26a0d29a3af3
Revises: f403ff7468e8
Create Date: 2024-10-24 12:31:37.706170

"""
from typing import Union

import sqlalchemy as sa
from airunner.utils.db import safe_alter_column
from airunner.data.models import ControlnetSettings, ImageToImageSettings, OutpaintSettings, DrawingPadSettings

revision: str = '26a0d29a3af3'
down_revision: Union[str, None] = 'f403ff7468e8'


def upgrade():
    safe_alter_column(ControlnetSettings, 'image', sa.LargeBinary, sa.String, nullable=True)
    safe_alter_column(ControlnetSettings, 'generated_image', sa.LargeBinary, sa.String, nullable=True)
    safe_alter_column(ImageToImageSettings, 'image', sa.LargeBinary, sa.String, nullable=True)
    safe_alter_column(OutpaintSettings, 'image', sa.LargeBinary, sa.String, nullable=True)
    safe_alter_column(DrawingPadSettings, 'image', sa.LargeBinary, sa.String, nullable=True)
    safe_alter_column(DrawingPadSettings, 'mask', sa.LargeBinary, sa.String, nullable=True)

def downgrade():
    safe_alter_column(ControlnetSettings, 'image', sa.String, sa.LargeBinary, nullable=True)
    safe_alter_column(ControlnetSettings, 'generated_image', sa.String, sa.LargeBinary, nullable=True)
    safe_alter_column(ImageToImageSettings, 'image', sa.String, sa.LargeBinary, nullable=True)
    safe_alter_column(OutpaintSettings, 'image', sa.String, sa.LargeBinary, nullable=True)
    safe_alter_column(DrawingPadSettings, 'image', sa.String, sa.LargeBinary, nullable=True)
    safe_alter_column(DrawingPadSettings, 'mask', sa.String, sa.LargeBinary, nullable=True)
