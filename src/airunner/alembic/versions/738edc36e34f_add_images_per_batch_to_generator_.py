"""add images_per_batch to generator_settings

Revision ID: 738edc36e34f
Revises: 904f01f8f439
Create Date: 2025-05-17 13:59:31.109970

"""

from typing import Sequence, Union

from airunner.components.art.data.generator_settings import GeneratorSettings
from airunner.utils.db import add_column, drop_column

# revision identifiers, used by Alembic.
revision: str = "738edc36e34f"
down_revision: Union[str, None] = "904f01f8f439"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column(GeneratorSettings, "images_per_batch")


def downgrade() -> None:
    drop_column(GeneratorSettings, "images_per_batch")
