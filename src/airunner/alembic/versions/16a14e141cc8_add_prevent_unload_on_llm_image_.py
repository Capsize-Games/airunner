"""add prevent_unload_on_llm_image_generation col to aplication settings

Revision ID: 16a14e141cc8
Revises: 04e4b744a3f6
Create Date: 2025-03-30 14:03:45.112475

"""
from typing import Sequence, Union

from airunner.data.models import MemorySettings
from airunner.utils.db import add_column, drop_column


# revision identifiers, used by Alembic.
revision: str = '16a14e141cc8'
down_revision: Union[str, None] = '04e4b744a3f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column(MemorySettings, 'prevent_unload_on_llm_image_generation')


def downgrade() -> None:
    drop_column(MemorySettings, 'prevent_unload_on_llm_image_generation')