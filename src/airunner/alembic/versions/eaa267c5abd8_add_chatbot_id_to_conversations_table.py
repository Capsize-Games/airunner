"""add chatbot_id to conversations table

Revision ID: eaa267c5abd8
Revises: c933800f14c4
Create Date: 2025-02-14 09:38:53.032022

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'eaa267c5abd8'
down_revision: Union[str, None] = 'c933800f14c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Disable foreign key constraints
    op.execute('PRAGMA foreign_keys=OFF')
    
    # Add the new column directly
    try:
        op.add_column('conversations', sa.Column('chatbot_id', sa.Integer(), sa.ForeignKey('chatbots.id', name='fk_conversations_chatbot_id')))
    except sa.exc.OperationalError as e:
        print("Error adding column: ", e)

    
    # Enable foreign key constraints
    op.execute('PRAGMA foreign_keys=ON')


def downgrade() -> None:
    # Disable foreign key constraints
    op.execute('PRAGMA foreign_keys=OFF')
    
    # Drop the column directly
    op.drop_column('conversations', 'chatbot_id')
    
    # Enable foreign key constraints
    op.execute('PRAGMA foreign_keys=ON')