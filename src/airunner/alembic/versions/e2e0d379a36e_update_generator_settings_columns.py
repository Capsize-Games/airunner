"""update generator settings columns

Revision ID: e2e0d379a36e
Revises: 3b1030ac9b9c
Create Date: 2025-03-23 05:22:59.970167

"""
from typing import Sequence, Union

import sqlalchemy as sa
from airunner.data.models import LLMGeneratorSettings
from airunner.utils.db import safe_alter_column


# revision identifiers, used by Alembic.
revision: str = 'e2e0d379a36e'
down_revision: Union[str, None] = '3b1030ac9b9c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    safe_alter_column(
        LLMGeneratorSettings,
        column_name="do_sample",
        new_type=sa.BOOLEAN,
        existing_type=sa.BOOLEAN,
        nullable=True,
        existing_server_default=sa.text('(False)'),
    )
    safe_alter_column(
        LLMGeneratorSettings,
        column_name="ngram_size",
        new_type=sa.INTEGER,
        existing_type=sa.INTEGER,
        nullable=True,
        existing_server_default=sa.text('0'),
    )
    safe_alter_column(
        LLMGeneratorSettings,
        column_name="length_penalty",
        new_type=sa.INTEGER,
        existing_type=sa.INTEGER,
        nullable=True,
        existing_server_default=sa.text('(900)'),
    )

def downgrade() -> None:
    safe_alter_column(
        LLMGeneratorSettings,
        column_name="do_sample",
        new_type=sa.BOOLEAN,
        existing_type=sa.BOOLEAN,
        nullable=False,
        existing_server_default=sa.text('(False)'),
    )
    safe_alter_column(
        LLMGeneratorSettings,
        column_name="ngram_size",
        new_type=sa.INTEGER,
        existing_type=sa.INTEGER,
        nullable=False,
        existing_server_default=sa.text('0'),
    )
    safe_alter_column(
        LLMGeneratorSettings,
        column_name="length_penalty",
        new_type=sa.INTEGER,
        existing_type=sa.INTEGER,
        nullable=False,
        existing_server_default=sa.text('(900)'),
    )