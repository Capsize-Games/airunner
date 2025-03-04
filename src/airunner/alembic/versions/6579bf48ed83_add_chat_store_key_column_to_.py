"""add chat_store_key column to Conversation table

Revision ID: 6579bf48ed83
Revises: c2c5d4cd4b80
Create Date: 2025-02-14 02:05:31.854218

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = '6579bf48ed83'
down_revision: Union[str, None] = 'c2c5d4cd4b80'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    columns_conversations = [col['name'] for col in inspector.get_columns('conversations')]

    try:
        if 'key' not in columns_conversations:
            op.add_column('conversations', sa.Column('key', sa.String(), nullable=True))
        else:
            print("Column 'key' already exists, skipping add.")
    except sa.exc.OperationalError as e:
        print("Error adding column 'key':", e)

    try:
        if 'value' not in columns_conversations:
            op.add_column('conversations', sa.Column('value', sa.JSON(), nullable=True))
        else:
            print("Column 'value' already exists, skipping add.")
    except sa.exc.OperationalError as e:
        print("Error adding column 'value':", e)

def downgrade() -> None:
    try:
        op.drop_column('conversations', 'key')
    except Exception as e:
        print("Error dropping column 'key':", e)

    try:
        op.drop_column('conversations', 'value')
    except Exception as e:
        print("Error dropping column 'value':", e)