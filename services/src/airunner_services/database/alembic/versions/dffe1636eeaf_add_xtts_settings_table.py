"""Add xtts_settings table

Revision ID: dffe1636eeaf
Revises: 843e4b044d4d
Create Date: 2025-11-30 18:34:11.469944

"""
from typing import Sequence, Union

from airunner_services.database.db import drop_table


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
    """Reject recreating the dropped SpeechT5 table without its user data."""
    raise RuntimeError(
        "Cannot downgrade this revision because speech_t5_settings was "
        "dropped and its rows cannot be reconstructed safely. Restore a "
        "pre-upgrade database backup to recover the lost data; otherwise "
        "keep this revision and upgrade forward."
    )
