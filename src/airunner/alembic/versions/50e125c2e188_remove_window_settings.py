"""remove window settings

Revision ID: 50e125c2e188
Revises: e2e0d379a36e
Create Date: 2025-03-23 06:17:52.827341

"""
from typing import Sequence, Union

from airunner.utils.db import drop_table


# revision identifiers, used by Alembic.
revision: str = '50e125c2e188'
down_revision: Union[str, None] = 'e2e0d379a36e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    drop_table(table_name='window_settings')


def downgrade() -> None:
    pass