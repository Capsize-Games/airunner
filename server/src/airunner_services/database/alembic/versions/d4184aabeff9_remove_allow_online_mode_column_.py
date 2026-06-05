"""Remove allow_online_mode column replaced by QSettings privacy controls

Revision ID: d4184aabeff9
Revises: 2a7206a1ff79
Create Date: 2025-12-02 15:26:02.555152

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "d4184aabeff9"
down_revision: Union[str, None] = "2a7206a1ff79"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite dev DBs can drift (or the column may never have existed), so make
    # this migration tolerant if the column is already absent.
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {
        col["name"] for col in inspector.get_columns("application_settings")
    }

    if "allow_online_mode" in cols:
        op.drop_column("application_settings", "allow_online_mode")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {
        col["name"] for col in inspector.get_columns("application_settings")
    }

    if "allow_online_mode" not in cols:
        op.add_column(
            "application_settings",
            sa.Column("allow_online_mode", sa.BOOLEAN(), nullable=True),
        )
