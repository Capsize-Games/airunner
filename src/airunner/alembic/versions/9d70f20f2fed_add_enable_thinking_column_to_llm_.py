"""Add enable_thinking column to llm_generator_settings

Revision ID: 9d70f20f2fed
Revises: 01b52e38f588
Create Date: 2025-11-28 07:40:37.588168

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from airunner.utils.db import add_column, drop_column
from airunner.components.llm.data.llm_generator_settings import LLMGeneratorSettings


# revision identifiers, used by Alembic.
revision: str = '9d70f20f2fed'
down_revision: Union[str, None] = '01b52e38f588'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add enable_thinking column with default True
    add_column(LLMGeneratorSettings, 'enable_thinking')


def downgrade() -> None:
    drop_column(LLMGeneratorSettings, 'enable_thinking')