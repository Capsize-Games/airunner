"""Create whisper_settings table

Revision ID: 536e18463461
Revises: 3212e8fccc68
Create Date: 2024-10-13 09:34:20.974389

"""
from typing import Union
from alembic import op
from airunner.utils.db.table import create_table_with_defaults, drop_table
from airunner.data.models import WhisperSettings

revision: str = '536e18463461'
down_revision: Union[str, None] = '3212e8fccc68'

def upgrade():
    create_table_with_defaults(WhisperSettings)

def downgrade():
    drop_table(WhisperSettings)
