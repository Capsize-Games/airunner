"""Adds ai_mode to settings

Revision ID: 55c1dff62eba
Revises: 08728ca819b8
Create Date: 2024-01-09 03:43:41.928457

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '55c1dff62eba'
down_revision: Union[str, None] = '08728ca819b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('settings', sa.Column('ai_mode', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('settings', 'ai_mode')
    # ### end Alembic commands ###