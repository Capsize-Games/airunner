"""add current_conversation to LLM generator settings

Revision ID: 9fab4d94d3e1
Revises: 68875bccab07
Create Date: 2025-03-06 09:30:12.926065

"""
from typing import Union

from alembic import op
import sqlalchemy as sa
from airunner.utils.db import column_exists
from airunner.data.models import LLMGeneratorSettings

revision: str = '9fab4d94d3e1'
down_revision: Union[str, None] = '68875bccab07'


def upgrade() -> None:
    if not column_exists(LLMGeneratorSettings, 'current_conversation'):
        with op.batch_alter_table('llm_generator_settings', recreate='always') as batch_op:
            batch_op.add_column(sa.Column('current_conversation', sa.Integer(), nullable=True))
            batch_op.create_foreign_key('fk_current_conversation', 'conversations', ['current_conversation'], ['id'])


def downgrade() -> None:
    with op.batch_alter_table('llm_generator_settings', recreate='always') as batch_op:
        batch_op.drop_constraint('fk_current_conversation', type_='foreignkey')
        batch_op.drop_column('current_conversation')