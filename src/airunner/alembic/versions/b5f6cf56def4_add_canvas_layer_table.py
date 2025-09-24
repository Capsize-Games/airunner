"""add canvas_layer table

Revision ID: b5f6cf56def4
Revises: 16692f02ba0d
Create Date: 2025-09-24 11:19:39.401378

"""

from typing import Sequence, Union

from airunner.components.art.data.canvas_layer import CanvasLayer
from airunner.utils.db.table import add_table, drop_table


# revision identifiers, used by Alembic.
revision: str = "b5f6cf56def4"
down_revision: Union[str, None] = "16692f02ba0d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_table(CanvasLayer)


def downgrade() -> None:
    drop_table(CanvasLayer)
