"""drop retired mode routing columns from llm_generator_settings

Revision ID: 48b1c0d3e4f5
Revises: 7b88f4d9a4a1
Create Date: 2026-05-13 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "48b1c0d3e4f5"
down_revision: Union[str, None] = "7b88f4d9a4a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _retired_columns() -> tuple[str, ...]:
    return ("use_mode_routing", "mode_override")


def _drop_retired_columns_if_present() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("llm_generator_settings"):
        return

    existing = {
        column["name"]
        for column in inspector.get_columns("llm_generator_settings")
    }
    targets = [name for name in _retired_columns() if name in existing]
    if not targets:
        return

    recreate = "always" if op.get_bind().dialect.name == "sqlite" else "auto"
    with op.batch_alter_table(
        "llm_generator_settings",
        recreate=recreate,
    ) as batch_op:
        for name in targets:
            batch_op.drop_column(name)


def upgrade() -> None:
    """Remove mode-routing columns retired from current settings."""
    _drop_retired_columns_if_present()


def downgrade() -> None:
    """Do not restore retired mode-routing columns on downgrade."""
    return None