"""removes primary and secondary colors from db

Revision ID: 5a85469cc534
Revises: 7175aec070c9
Create Date: 2024-01-11 10:20:48.871476

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5a85469cc534'
down_revision: Union[str, None] = '7175aec070c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('settings', 'primary_color')
    op.drop_column('settings', 'secondary_color')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('settings', sa.Column('secondary_color', sa.VARCHAR(), nullable=True))
    op.add_column('settings', sa.Column('primary_color', sa.VARCHAR(), nullable=True))
    # ### end Alembic commands ###