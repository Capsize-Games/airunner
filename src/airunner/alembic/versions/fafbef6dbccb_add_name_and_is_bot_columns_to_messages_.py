"""Add name and is_bot columns to messages table

Revision ID: fafbef6dbccb
Revises: 092e6840c1f0
Create Date: 2024-09-18 12:47:54.308745

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fafbef6dbccb'
down_revision: Union[str, None] = '092e6840c1f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Create a new table with the desired schema
    op.create_table(
        'conversations_new',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('title', sa.String, nullable=False),
    )

    # Copy data from the old table to the new table
    op.execute('INSERT INTO conversations_new (id, title) SELECT id, title FROM conversations')

    # Drop the old table
    op.drop_table('conversations')

    # Rename the new table to the old table name
    op.rename_table('conversations_new', 'conversations')


def downgrade():
    # Create the old table with the original schema
    op.create_table(
        'conversations_old',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('title', sa.String, nullable=True),
    )

    # Copy data from the new table to the old table
    op.execute('INSERT INTO conversations_old (id, title) SELECT id, title FROM conversations')

    # Drop the new table
    op.drop_table('conversations')

    # Rename the old table to the original table name
    op.rename_table('conversations_old', 'conversations')
