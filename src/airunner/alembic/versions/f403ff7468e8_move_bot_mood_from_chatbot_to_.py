"""Move bot_mood from Chatbot to Conversation

Revision ID: f403ff7468e8
Revises: 536e18463461
Create Date: 2024-10-24 01:43:30.378281

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.exc import OperationalError

# revision identifiers, used by Alembic.
revision: str = 'f403ff7468e8'
down_revision: Union[str, None] = '536e18463461'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    columns_conversations = [col['name'] for col in inspector.get_columns('conversations')]
    columns_chatbots = [col['name'] for col in inspector.get_columns('chatbots')]

    if 'bot_mood' not in columns_conversations:
        op.add_column('conversations', sa.Column('bot_mood', sa.Text(), nullable=True))

    if 'bot_mood' in columns_chatbots:
        try:
            op.drop_column('chatbots', 'bot_mood')
        except OperationalError as e:
            print(f"Error dropping column 'bot_mood' from 'chatbots': {e}")
    else:
        print("Column 'bot_mood' not found in 'chatbots', skipping drop.")

def downgrade():
    op.add_column('chatbots', sa.Column('bot_mood', sa.Text(), nullable=True))
    op.drop_column('conversations', 'bot_mood')
