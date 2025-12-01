"""Add xtts_settings table

Revision ID: dffe1636eeaf
Revises: 843e4b044d4d
Create Date: 2025-11-30 18:34:11.469944

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from airunner.utils.db import drop_table


# revision identifiers, used by Alembic.
revision: str = 'dffe1636eeaf'
down_revision: Union[str, None] = '843e4b044d4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Note: XTTS has been removed from the project.
    # This migration originally added an xtts_settings table, but since XTTS
    # is no longer supported, we skip creating that table.
    # We still drop the deprecated speech_t5_settings table.
    drop_table(table_name="speech_t5_settings")


def downgrade() -> None:
    # Recreate speech_t5_settings table
    op.create_table('speech_t5_settings',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('datasets_path', sa.VARCHAR(), nullable=True),
    sa.Column('processor_path', sa.VARCHAR(), nullable=True),
    sa.Column('vocoder_path', sa.VARCHAR(), nullable=True),
    sa.Column('model_path', sa.VARCHAR(), nullable=True),
    sa.Column('pitch', sa.INTEGER(), nullable=True),
    sa.Column('voice', sa.VARCHAR(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    
    # Drop xtts_settings table if it exists
    drop_table(table_name="xtts_settings")