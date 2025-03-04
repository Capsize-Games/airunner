"""Adds summary column to conversations table

Revision ID: 6c6cf295a892
Revises: f3d84a9d5049
Create Date: 2025-02-19 02:33:21.496409

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = '6c6cf295a892'
down_revision: Union[str, None] = 'f3d84a9d5049'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    columns_conversations = [col['name'] for col in inspector.get_columns('conversations')]

    try:
        if 'summary' not in columns_conversations:
            op.add_column('conversations', sa.Column('summary', sa.Text(), nullable=True))
        else:
            print("Column 'summary' already exists, skipping add.")
    except sa.exc.OperationalError as e:
        print("Error adding column 'summary': ", e)
    
    try:
        if 'user_data' not in columns_conversations:
            op.add_column('conversations', sa.Column('user_data', sa.JSON(), nullable=True))
        else:
            print("Column 'user_data' already exists, skipping add.")
    except sa.exc.OperationalError as e:
        print("Error adding column 'user_data': ", e)


def downgrade() -> None:
    try:
        op.drop_column('conversations', 'summary')
    except Exception as e:
        print("Error dropping column 'summary': ", e)
    
    try:
        op.drop_column('conversations', 'user_data')
    except Exception as e:
        print("Error dropping column 'user_data': ", e)