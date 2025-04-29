"""add use_refiner column to generator settings

Revision ID: e6ef79c17a07
Revises: 8ae5502625f5
Create Date: 2025-04-28 22:30:52.717251

"""

from typing import Sequence, Union

from airunner.data.models import GeneratorSettings
from airunner.utils.db import add_column, drop_column


# revision identifiers, used by Alembic.
revision: str = "e6ef79c17a07"
down_revision: Union[str, None] = "8ae5502625f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column(GeneratorSettings, "use_refiner")


def downgrade() -> None:
    drop_column(GeneratorSettings, "use_refiner")
