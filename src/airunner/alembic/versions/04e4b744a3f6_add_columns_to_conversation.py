"""Add columns to conversation

Revision ID: 04e4b744a3f6
Revises: 50e125c2e188
Create Date: 2025-03-30 13:42:57.817433

"""
from typing import Sequence, Union

from airunner.utils.db import add_column, drop_column
from airunner.data.models import Conversation

# revision identifiers, used by Alembic.
revision: str = '04e4b744a3f6'
down_revision: Union[str, None] = '50e125c2e188'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column(Conversation, 'last_analysis_time',)
    add_column(Conversation, 'last_analyzed_message_id',)


def downgrade() -> None:
    drop_column(Conversation, 'last_analysis_time',)
    drop_column(Conversation, 'last_analyzed_message_id',)