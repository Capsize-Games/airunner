"""Adds is_preset flag to generator settings table

Revision ID: 7c1b15cade9b
Revises: 435acbb59892
Create Date: 2024-01-02 06:52:02.924308

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c1b15cade9b'
down_revision: Union[str, None] = '435acbb59892'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('generator_settings', sa.Column('is_preset', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('generator_settings', 'is_preset')
    # ### end Alembic commands ###