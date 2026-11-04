"""remove tts_settings

Revision ID: 2d6569089de6
Revises: ac88a4dea04b
Create Date: 2025-04-02 07:25:25.712957

"""

from typing import Sequence, Union

from airunner_services.database.db import drop_table

# revision identifiers, used by Alembic.
revision: str = "2d6569089de6"
down_revision: Union[str, None] = "ac88a4dea04b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    drop_table(table_name="tts_settings")


def downgrade() -> None:
    """Reject recovery that would silently discard or fabricate data."""
    raise RuntimeError(
        "Cannot downgrade: the tts_settings table was dropped and cannot be "
        "reconstructed safely. Restore a pre-upgrade database backup to "
        "recover the lost data; otherwise keep this revision and upgrade forward."
    )
