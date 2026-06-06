"""add canvas_document table

Revision ID: f0b1f4cf8f42
Revises: f0b1f4cf8f41
Create Date: 2025-10-01 12:00:00.000000

"""

from typing import Sequence, Union

from airunner_services.database.models.canvas_document import CanvasDocument
from airunner_services.database.db.table import add_table, drop_table

# revision identifiers, used by Alembic.
revision: str = "f0b1f4cf8f42"
down_revision: Union[str, None] = "f0b1f4cf8f41"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_table(CanvasDocument)


def downgrade() -> None:
    drop_table(CanvasDocument)
