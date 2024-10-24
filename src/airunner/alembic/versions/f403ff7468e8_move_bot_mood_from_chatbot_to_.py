"""Move bot_mood from Chatbot to Conversation

Revision ID: f403ff7468e8
Revises: 536e18463461
Create Date: 2024-10-24 01:43:30.378281

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = 'f403ff7468e8'
down_revision: Union[str, None] = '536e18463461'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    try:
        # Add bot_mood column to conversation table
        op.add_column('conversations', sa.Column('bot_mood', sa.Text(), nullable=True))
    except sqlite.DatabaseError:
        pass

    try:
        # Remove bot_mood column from chatbot table
        op.drop_column('chatbots', 'bot_mood')
    except sqlite.DatabaseError:
        pass

def downgrade():
    try:
        op.add_column('chatbots', sa.Column('bot_mood', sa.Text(), nullable=True))
    except sqlite.DatabaseError:
        pass

    try:
        op.drop_column('conversations', 'bot_mood')
    except sqlite.DatabaseError:
        pass
