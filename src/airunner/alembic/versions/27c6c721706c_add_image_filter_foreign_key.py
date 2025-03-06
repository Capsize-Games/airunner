"""add image filter foreign key

Revision ID: 27c6c721706c
Revises: db83dfae10f5
Create Date: 2025-03-03 15:23:35.805706

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '27c6c721706c'
down_revision: Union[str, None] = 'db83dfae10f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # Set default value for existing rows
    op.execute("UPDATE image_filter_values SET image_filter_id = 1 WHERE image_filter_id IS NULL OR image_filter_id NOT IN (SELECT id FROM image_filter_settings)")

    # Alter column to set default value and not nullable
    if bind.dialect.name == 'sqlite':
        # SQLite does not support altering column types directly
        with op.batch_alter_table('image_filter_values', recreate='always') as batch_op:
            batch_op.alter_column('image_filter_id',
                existing_type=sa.INTEGER(),
                nullable=False,
                server_default=sa.text('1'))
    else:
        op.alter_column('image_filter_values', 'image_filter_id',
            existing_type=sa.INTEGER(),
            nullable=False,
            server_default=sa.text('1'))

    # Create foreign key constraint
    if bind.dialect.name == 'sqlite':
        with op.batch_alter_table('image_filter_values', recreate='always') as batch_op:
            batch_op.create_foreign_key('fk_image_filter_values_image_filter_id', 'image_filter_settings', ['image_filter_id'], ['id'])
    else:
        op.create_foreign_key('fk_image_filter_values_image_filter_id', 'image_filter_values', 'image_filter_settings', ['image_filter_id'], ['id'])


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