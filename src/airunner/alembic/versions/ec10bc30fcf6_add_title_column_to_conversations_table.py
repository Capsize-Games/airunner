"""Add title column to conversations table

Revision ID: ec10bc30fcf6
Revises: 9f7e51be5150
Create Date: 2024-09-18 11:29:21.066762

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ec10bc30fcf6'
down_revision: Union[str, None] = '9f7e51be5150'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('conversations', sa.Column('title', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('conversations', 'title')
    # ### end Alembic commands ###