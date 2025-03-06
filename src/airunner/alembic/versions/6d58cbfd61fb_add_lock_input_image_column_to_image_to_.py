"""Add lock_input_image column to image_to_image_settings

Revision ID: 6d58cbfd61fb
Revises: 72d9134823cb
Create Date: 2024-10-09 10:05:11.349862

"""
from typing import Union

from airunner.data.models import ImageToImageSettings, ControlnetSettings
from airunner.utils.db import add_columns, drop_columns

revision: str = '6d58cbfd61fb'
down_revision: Union[str, None] = '72d9134823cb'


def upgrade():
    add_columns(ImageToImageSettings, ["lock_input_image"])
    add_columns(ControlnetSettings, ["lock_input_image"])

def downgrade():
    drop_columns(ImageToImageSettings, ["lock_input_image"])
    drop_columns(ControlnetSettings, ["lock_input_image"])
