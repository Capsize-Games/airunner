"""remove window settings

Revision ID: 50e125c2e188
Revises: e2e0d379a36e
Create Date: 2025-03-23 06:17:52.827341

"""

from typing import Sequence, Union

from airunner_services.database.db import drop_table


# revision identifiers, used by Alembic.
revision: str = "50e125c2e188"
down_revision: Union[str, None] = "e2e0d379a36e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    drop_table(table_name="window_settings")


def downgrade() -> None:
    """Reject recovery that would silently discard or fabricate data."""
    raise RuntimeError(
        "Cannot downgrade: the window_settings table was dropped and cannot "
        "be reconstructed safely. Restore a pre-upgrade database backup to "
        "recover the lost data; otherwise keep this revision and upgrade forward."
    )
