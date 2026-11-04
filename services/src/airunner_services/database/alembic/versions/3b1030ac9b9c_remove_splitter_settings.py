"""remove splitter settings

Revision ID: 3b1030ac9b9c
Revises: 073c56efe38b
Create Date: 2025-03-23 05:19:24.690043

"""

from typing import Sequence, Union

from airunner_services.database.db import drop_table

# revision identifiers, used by Alembic.
revision: str = "3b1030ac9b9c"
down_revision: Union[str, None] = "073c56efe38b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    drop_table(table_name="splitter_settings")


def downgrade() -> None:
    """Reject recovery that would silently discard or fabricate data."""
    raise RuntimeError(
        "Cannot downgrade: the splitter_settings table was dropped and cannot "
        "be reconstructed safely. Restore a pre-upgrade database backup to "
        "recover the lost data; otherwise keep this revision and upgrade forward."
    )
