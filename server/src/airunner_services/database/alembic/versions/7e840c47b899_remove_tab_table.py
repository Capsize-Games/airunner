"""remove tab table

Revision ID: 7e840c47b899
Revises: f8077817b00e
Create Date: 2025-06-17 13:36:48.202038

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7e840c47b899"
down_revision: Union[str, None] = "f8077817b00e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop the tabs table if it exists.

    The original migration assumed the table existed, but in some
    environments the creation migration was a no-op, so we guard it.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "tabs" in inspector.get_table_names():
        op.drop_table("tabs")


def downgrade() -> None:
    pass
