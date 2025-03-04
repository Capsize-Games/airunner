"""Adds backstory and use_backstory columns to chatbot

Revision ID: f447116b8b54
Revises: 6c6cf295a892
Create Date: 2025-02-20 06:22:03.824057

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = 'f447116b8b54'
down_revision: Union[str, None] = '6c6cf295a892'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    columns_chatbots = [col['name'] for col in inspector.get_columns('chatbots')]

    try:
        if 'backstory' not in columns_chatbots:
            op.add_column('chatbots', sa.Column('backstory', sa.Text(), nullable=True))
        else:
            print("Column 'backstory' already exists, skipping add.")
    except sa.exc.OperationalError as e:
        print("Error adding column 'backstory': ", e)
    
    try:
        if 'use_backstory' not in columns_chatbots:
            op.add_column('chatbots', sa.Column('use_backstory', sa.Boolean(), nullable=True))
        else:
            print("Column 'use_backstory' already exists, skipping add.")
    except sa.exc.OperationalError as e:
        print("Error adding column 'use_backstory': ", e)
    
def downgrade() -> None:
    try:
        op.drop_column('chatbots', 'use_backstory')
    except Exception as e:
        print("Error dropping column 'use_backstory': ", e)
    
    try:
        op.drop_column('chatbots', 'backstory')
    except Exception as e:
        print("Error dropping column 'backstory': ", e)