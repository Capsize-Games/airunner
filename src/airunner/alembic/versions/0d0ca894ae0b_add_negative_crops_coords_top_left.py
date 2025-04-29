"""add negative_crops_coords_top_left

Revision ID: 0d0ca894ae0b
Revises: 647a8e1098ce
Create Date: 2025-04-29 05:26:19.241280

"""

from typing import Sequence, Union

from airunner.data.models.generator_settings import GeneratorSettings
from airunner.utils.db import add_column, drop_column


# revision identifiers, used by Alembic.
revision: str = "0d0ca894ae0b"
down_revision: Union[str, None] = "647a8e1098ce"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column(GeneratorSettings, "negative_crops_coords_top_left")


def downgrade() -> None:
    drop_column(GeneratorSettings, "negative_crops_coords_top_left")
