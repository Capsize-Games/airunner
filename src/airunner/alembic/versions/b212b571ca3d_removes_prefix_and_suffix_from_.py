"""Removes prefix and suffix from llmgenerator

Revision ID: b212b571ca3d
Revises: bc6ff97b7e60
Create Date: 2024-01-11 07:07:49.331870

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b212b571ca3d'
down_revision: Union[str, None] = 'bc6ff97b7e60'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('llm_generator', 'suffix')
    op.drop_column('llm_generator', 'prefix')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('llm_generator', sa.Column('prefix', sa.VARCHAR(), nullable=True))
    op.add_column('llm_generator', sa.Column('suffix', sa.VARCHAR(), nullable=True))
    # ### end Alembic commands ###