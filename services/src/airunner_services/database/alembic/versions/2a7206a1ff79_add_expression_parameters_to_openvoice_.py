"""Add expression parameters to OpenVoice settings

Revision ID: 2a7206a1ff79
Revises: dffe1636eeaf
Create Date: 2025-12-01 09:12:18.067121

"""
from typing import Sequence, Union

from alembic import op
from airunner_services.database.db import add_column
from airunner_services.database.models.openvoice_settings import (
    OpenVoiceSettings,
)


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
    
    # Preserve existing NULLs (including databases where these columns were
    # added by an interrupted or manual migration). OpenVoiceSettings supplies
    # Python-side defaults for new ORM-created rows; no historical value can be
    # inferred safely from NULL.


def downgrade() -> None:
    """Reject restoring the XTTS table after its user data was dropped."""
    raise RuntimeError(
        "Cannot downgrade this revision because xtts_settings was dropped; "
        "its schema and rows cannot be reconstructed safely. Restore a "
        "pre-upgrade database backup to recover the lost data; otherwise "
        "keep this revision and upgrade forward."
    )