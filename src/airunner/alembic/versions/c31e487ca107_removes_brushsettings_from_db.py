"""removes brushsettings from db

Revision ID: c31e487ca107
Revises: 385df574fb0b
Create Date: 2024-01-11 12:00:45.609967

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c31e487ca107'
down_revision: Union[str, None] = '385df574fb0b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('brush_settings')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('brush_settings',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('size', sa.INTEGER(), nullable=True),
    sa.Column('primary_color', sa.VARCHAR(), nullable=True),
    sa.Column('secondary_color', sa.VARCHAR(), nullable=True),
    sa.Column('created_at', sa.DATETIME(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###