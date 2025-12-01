"""Add expression parameters to OpenVoice settings

Revision ID: 2a7206a1ff79
Revises: dffe1636eeaf
Create Date: 2025-12-01 09:12:18.067121

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from airunner.utils.db import add_column, column_exists
from airunner.components.tts.data.models.openvoice_settings import OpenVoiceSettings


# revision identifiers, used by Alembic.
revision: str = '2a7206a1ff79'
down_revision: Union[str, None] = 'dffe1636eeaf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the now-obsolete xtts_settings table
    op.execute("DROP TABLE IF EXISTS xtts_settings")
    
    # Add expression parameters to openvoice_settings
    add_column(OpenVoiceSettings, 'sdp_ratio')
    add_column(OpenVoiceSettings, 'noise_scale')
    add_column(OpenVoiceSettings, 'noise_scale_w')
    
    # Set defaults for existing rows
    op.execute("UPDATE openvoice_settings SET sdp_ratio = 20 WHERE sdp_ratio IS NULL")
    op.execute("UPDATE openvoice_settings SET noise_scale = 60 WHERE noise_scale IS NULL")
    op.execute("UPDATE openvoice_settings SET noise_scale_w = 80 WHERE noise_scale_w IS NULL")


def downgrade() -> None:
    # SQLite doesn't support DROP COLUMN, so we skip column removal
    # The columns will remain but be unused
    pass