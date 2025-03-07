"""add chatbot_id to conversations table

Revision ID: eaa267c5abd8
Revises: c933800f14c4
Create Date: 2025-02-14 09:38:53.032022

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine import Engine
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = 'eaa267c5abd8'
down_revision: Union[str, None] = 'c933800f14c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    columns_conversations = [col['name'] for col in inspector.get_columns('conversations')]

    if isinstance(bind, Engine) and bind.dialect.name == 'sqlite':
        # Disable foreign key constraints for SQLite
        op.execute('PRAGMA foreign_keys=OFF')
    
    # Add the new column directly
    try:
        if 'chatbot_id' not in columns_conversations:
            op.add_column('conversations', sa.Column('chatbot_id', sa.Integer(), sa.ForeignKey('chatbots.id', name='fk_conversations_chatbot_id')))
        else:
            print("Column 'chatbot_id' already exists, skipping add.")
    except sa.exc.OperationalError as e:
        print("Error adding column: ", e)

    if isinstance(bind, Engine) and bind.dialect.name == 'sqlite':
        # Enable foreign key constraints for SQLite
        op.execute('PRAGMA foreign_keys=ON')


def downgrade() -> None:
    bind = op.get_bind()
    if isinstance(bind, Engine) and bind.dialect.name == 'sqlite':
        # Disable foreign key constraints for SQLite
        op.execute('PRAGMA foreign_keys=OFF')
    
    # Drop the column directly
    try:
        op.drop_column('conversations', 'chatbot_id')
    except Exception as e:
        print("Error dropping column: ", e)
    
    if isinstance(bind, Engine) and bind.dialect.name == 'sqlite':
        # Enable foreign key constraints for SQLite
        op.execute('PRAGMA foreign_keys=ON')