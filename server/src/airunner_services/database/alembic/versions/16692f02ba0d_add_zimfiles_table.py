"""Add zimfiles table

Revision ID: 16692f02ba0d
Revises: 7e840c47b899
Create Date: 2025-06-26 14:31:16.947306

"""

from typing import Sequence, Union

from airunner_services.database.models.zimfile import ZimFile
from airunner_services.database.db.table import add_table, drop_table

# revision identifiers, used by Alembic.
revision: str = "16692f02ba0d"
down_revision: Union[str, None] = "7e840c47b899"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_table(ZimFile)


def downgrade() -> None:
    drop_table(ZimFile)
