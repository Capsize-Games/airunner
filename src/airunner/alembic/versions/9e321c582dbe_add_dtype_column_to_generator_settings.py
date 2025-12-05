"""Add dtype column to generator_settings

Revision ID: 9e321c582dbe
Revises: d4184aabeff9
Create Date: 2025-12-04 15:07:33.616938

"""
from typing import Sequence, Union

from airunner.utils.db import add_column, drop_column
from airunner.components.art.data.generator_settings import GeneratorSettings


# revision identifiers, used by Alembic.
revision: str = '9e321c582dbe'
down_revision: Union[str, None] = 'd4184aabeff9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column(GeneratorSettings, 'dtype')


def downgrade() -> None:
    drop_column(GeneratorSettings, 'dtype')