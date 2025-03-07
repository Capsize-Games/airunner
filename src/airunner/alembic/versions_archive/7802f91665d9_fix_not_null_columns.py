"""fix not null columns

Revision ID: 7802f91665d9
Revises: 27c6c721706c
Create Date: 2025-03-04 10:00:24.725742

"""
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = '7802f91665d9'
down_revision: Union[str, None] = '27c6c721706c'


def upgrade() -> None:
    with op.batch_alter_table('chatbots', recreate='always') as batch_op:
        batch_op.alter_column('id', existing_type=sa.INTEGER(), nullable=False, autoincrement=True)
    
    with op.batch_alter_table('image_filter_values', recreate='always') as batch_op:
        batch_op.alter_column('id', existing_type=sa.INTEGER(), nullable=False, autoincrement=True)
        batch_op.alter_column('name', existing_type=sa.TEXT(), nullable=False)
        batch_op.alter_column('value', existing_type=sa.TEXT(), nullable=False)
        batch_op.alter_column('value_type', existing_type=sa.TEXT(), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table('image_filter_values', recreate='always') as batch_op:
        batch_op.alter_column('value_type', existing_type=sa.TEXT(), nullable=True)
        batch_op.alter_column('value', existing_type=sa.TEXT(), nullable=True)
        batch_op.alter_column('name', existing_type=sa.TEXT(), nullable=True)
        batch_op.alter_column('id', existing_type=sa.INTEGER(), nullable=True, autoincrement=True)
    
    with op.batch_alter_table('chatbots', recreate='always') as batch_op:
        batch_op.alter_column('id', existing_type=sa.INTEGER(), nullable=True, autoincrement=True)