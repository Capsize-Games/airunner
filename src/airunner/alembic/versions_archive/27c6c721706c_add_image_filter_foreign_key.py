"""add image filter foreign key

Revision ID: 27c6c721706c
Revises: db83dfae10f5
Create Date: 2025-03-03 15:23:35.805706

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from airunner.utils.db import set_default_and_create_fk  # New import


# revision identifiers, used by Alembic.
revision: str = '27c6c721706c'
down_revision: Union[str, None] = 'db83dfae10f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    set_default_and_create_fk(
        table_name='image_filter_values',
        column_name='image_filter_id',
        ref_table_name='image_filter_settings',
        ref_column_name='id',
        default_value=1
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'sqlite':
        # SQLite does not support altering column types directly
        with op.batch_alter_table('image_filter_values', recreate='always') as batch_op:
            batch_op.drop_constraint('fk_image_filter_values_image_filter_id', type_='foreignkey')
            batch_op.alter_column('image_filter_id',
                    existing_type=sa.INTEGER(),
                    nullable=True,
                    server_default=None)
    else:
        op.drop_constraint('fk_image_filter_values_image_filter_id', 'image_filter_values', type_='foreignkey')
        op.alter_column('image_filter_values', 'image_filter_id',
                existing_type=sa.INTEGER(),
                nullable=True,
                server_default=None)