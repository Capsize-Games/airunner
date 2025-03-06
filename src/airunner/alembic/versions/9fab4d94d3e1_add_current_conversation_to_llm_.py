"""add current_conversation to LLM generator settings

Revision ID: 9fab4d94d3e1
Revises: 68875bccab07
Create Date: 2025-03-06 09:30:12.926065

"""
from typing import Union

import sqlalchemy as sa
from airunner.utils.db import add_column_with_fk, drop_column_with_fk
from airunner.data.models import LLMGeneratorSettings

revision: str = '9fab4d94d3e1'
down_revision: Union[str, None] = '68875bccab07'

def upgrade() -> None:
    add_column_with_fk(
        LLMGeneratorSettings,
        column_name='current_conversation',
        column_type=sa.Integer(),
        fk_table='conversations',
        fk_column='id',
        fk_name='fk_current_conversation'
    )

def downgrade() -> None:
    drop_column_with_fk(
        LLMGeneratorSettings,
        column_name='current_conversation',
        fk_name='fk_current_conversation'
    )