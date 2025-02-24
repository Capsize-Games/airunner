"""add chatbot_id to conversations table

Revision ID: eaa267c5abd8
Revises: c933800f14c4
Create Date: 2025-02-14 09:38:53.032022

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = 'eaa267c5abd8'
down_revision: Union[str, None] = 'c933800f14c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('conversations') as batch_op:
        batch_op.add_column(sa.Column('chatbot_id', sa.Integer(), sa.ForeignKey('chatbots.id', name='fk_conversations_chatbot_id')))


def downgrade() -> None:
    with op.batch_alter_table('conversations') as batch_op:
        batch_op.drop_column('chatbot_id')