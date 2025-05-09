"""Change enabled to false by default

Revision ID: f54532589efa
Revises: aee3c6d6452c
Create Date: 2025-05-08 21:16:32.806276

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from airunner.utils.db import alter_column
from airunner.data.models.outpaint_settings import OutpaintSettings

# revision identifiers, used by Alembic.
revision: str = "f54532589efa"
down_revision: Union[str, None] = "aee3c6d6452c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    alter_column(
        OutpaintSettings,
        sa.Column("enabled", sa.Boolean(), default=True),
        sa.Column(
            "enabled", sa.Boolean(), default=False, server_default="false"
        ),
    )


def downgrade() -> None:
    alter_column(
        OutpaintSettings,
        sa.Column("enabled", sa.Boolean(), default=False),
        sa.Column(
            "enabled", sa.Boolean(), default=True, server_default="true"
        ),
    )
