"""Add default value to User.username

Revision ID: 5e03be0b5d05
Revises: 4157bb294b34
Create Date: 2025-03-04 10:16:06.409255

"""
from typing import Union

from alembic import op
import sqlalchemy as sa
from airunner.data.models import User


revision: str = '5e03be0b5d05'
down_revision: Union[str, None] = '4157bb294b34'


def upgrade() -> None:
    with op.batch_alter_table(User.__tablename__, recreate='always') as batch_op:
        batch_op.alter_column(
            'username', 
            existing_type=sa.String(), 
            server_default='User',
            nullable=False
        )


def downgrade() -> None:
    with op.batch_alter_table(User.__tablename__, recreate='always') as batch_op:
        batch_op.alter_column(
            'username', 
            existing_type=sa.String(), 
            server_default=None,
            nullable=True
        )