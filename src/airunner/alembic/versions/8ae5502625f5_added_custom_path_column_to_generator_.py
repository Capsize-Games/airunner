"""added custom_path column to generator settings

Revision ID: 8ae5502625f5
Revises: 2d372e78d20b
Create Date: 2025-04-26 12:32:08.132267

"""

from typing import Sequence, Union

from airunner.data.models.generator_settings import GeneratorSettings
from airunner.utils.db import add_column, drop_column


# revision identifiers, used by Alembic.
revision: str = "8ae5502625f5"
down_revision: Union[str, None] = "2d372e78d20b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column(GeneratorSettings, "custom_path")


def downgrade() -> None:
    drop_column(GeneratorSettings, "custom_path")
