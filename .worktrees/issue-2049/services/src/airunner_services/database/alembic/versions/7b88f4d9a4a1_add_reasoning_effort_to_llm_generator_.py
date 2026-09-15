"""add reasoning_effort to llm_generator_settings

Revision ID: 7b88f4d9a4a1
Revises: c3f4b2a1d9e8
Create Date: 2026-05-02 13:20:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from airunner_services.database.db.engine import get_inspector


# revision identifiers, used by Alembic.
revision: str = "7b88f4d9a4a1"
down_revision: Union[str, None] = "c3f4b2a1d9e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the persisted GPT-OSS reasoning-effort setting."""
    inspector = get_inspector()
    columns = {
        column["name"]
        for column in inspector.get_columns("llm_generator_settings")
    }
    if "reasoning_effort" in columns:
        return

    op.add_column(
        "llm_generator_settings",
        sa.Column(
            "reasoning_effort",
            sa.String(),
            nullable=False,
            server_default="medium",
        ),
    )


def downgrade() -> None:
    """SQLite downgrade is intentionally skipped."""
    return None