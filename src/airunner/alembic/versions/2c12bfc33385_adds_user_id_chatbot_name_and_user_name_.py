"""Adds user_id, chatbot_name and user_name columns to conversation table

Revision ID: 2c12bfc33385
Revises: bd0a424f223d
Create Date: 2025-02-15 04:46:57.397764

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = '2c12bfc33385'
down_revision: Union[str, None] = 'bd0a424f223d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    columns_conversations = [col['name'] for col in inspector.get_columns('conversations')]

    try:
        if 'chatbot_name' not in columns_conversations:
            op.add_column('conversations', sa.Column('chatbot_name', sa.String(length=255), nullable=True))
        else:
            print("Column 'chatbot_name' already exists, skipping add.")
    except sa.exc.OperationalError as e:
        print("Error adding column 'chatbot_name': ", e)
    
    try:
        if 'user_id' not in columns_conversations:
            op.add_column('conversations', sa.Column('user_id', sa.String(length=255), nullable=True))
        else:
            print("Column 'user_id' already exists, skipping add.")
    except sa.exc.OperationalError as e:
        print("Error adding column 'user_id': ", e)
    
    try:
        if 'user_name' not in columns_conversations:
            op.add_column('conversations', sa.Column('user_name', sa.String(length=255), nullable=True))
        else:
            print("Column 'user_name' already exists, skipping add.")
    except sa.exc.OperationalError as e:
        print("Error adding column 'user_name': ", e)
    
    try:
        if 'status' not in columns_conversations:
            op.add_column('conversations', sa.Column('status', sa.String(length=255), nullable=True))
        else:
            print("Column 'status' already exists, skipping add.")
    except sa.exc.OperationalError as e:
        print("Error adding column 'status': ", e)


def downgrade() -> None:
    op.drop_column('conversations', 'user_name')
    op.drop_column('conversations', 'user_id')
    op.drop_column('conversations', 'chatbot_name')
    op.drop_column('conversations', 'status')