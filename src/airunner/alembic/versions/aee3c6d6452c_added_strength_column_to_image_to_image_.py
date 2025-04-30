"""added strength column to image_to_image_settings table

Revision ID: aee3c6d6452c
Revises: 0d0ca894ae0b
Create Date: 2025-04-29 14:12:10.904776

"""

from typing import Sequence, Union

from airunner.data.models import ImageToImageSettings
from airunner.utils.db import add_column, drop_column


# revision identifiers, used by Alembic.
revision: str = "aee3c6d6452c"
down_revision: Union[str, None] = "0d0ca894ae0b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column(ImageToImageSettings, "strength")


def downgrade() -> None:
    drop_column(ImageToImageSettings, "strength")
