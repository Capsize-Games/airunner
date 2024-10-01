"""Drop translation_settings table if exists

Revision ID: 4c51e062edc4
Revises: 6f0a227f7ac9
Create Date: 2024-09-30 06:02:12.306594

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '4c51e062edc4'
down_revision: Union[str, None] = '1d40f74da876'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Drop the translation_settings table if it exists
    op.execute("DROP TABLE IF EXISTS translation_settings")

def downgrade():
    # No reverse migration
    pass
    # ### end Alembic commands ###
