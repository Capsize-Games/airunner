"""add metadata column to User class

Revision ID: bd0a424f223d
Revises: eaa267c5abd8
Create Date: 2025-02-14 10:48:02.584981

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = 'bd0a424f223d'
down_revision: Union[str, None] = 'eaa267c5abd8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    columns_users = [col['name'] for col in inspector.get_columns('users')]

    try:
        with op.batch_alter_table('users') as batch_op:
            if 'data' not in columns_users:
                batch_op.add_column(sa.Column('data', sa.JSON(), nullable=True))
            else:
                print("Column 'data' already exists, skipping add.")
    except sa.exc.OperationalError as e:
        print("Error adding column: ", e)


def downgrade() -> None:
    try:
        with op.batch_alter_table('users') as batch_op:
            batch_op.drop_column('data')
    except Exception as e:
        print("Error dropping column: ", e)