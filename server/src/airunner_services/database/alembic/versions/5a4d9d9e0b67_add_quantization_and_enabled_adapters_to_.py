"""add quantization and enabled adapters to llm_generator_settings

Revision ID: 5a4d9d9e0b67
Revises: 7b88f4d9a4a1
Create Date: 2026-05-15 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from airunner_services.database.db.engine import get_inspector

# revision identifiers, used by Alembic.
revision: str = "5a4d9d9e0b67"
down_revision: Union[str, None] = "7b88f4d9a4a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Persist adapter selection and quantization preference."""
    inspector = get_inspector()
    if not inspector.has_table("llm_generator_settings"):
        return

    columns = {
        column["name"]
        for column in inspector.get_columns("llm_generator_settings")
    }

    if "quantization_bits" not in columns:
        op.add_column(
            "llm_generator_settings",
            sa.Column(
                "quantization_bits",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )

    if "enabled_adapters" not in columns:
        op.add_column(
            "llm_generator_settings",
            sa.Column(
                "enabled_adapters",
                sa.JSON(),
                nullable=False,
                server_default="[]",
            ),
        )


def downgrade() -> None:
    """SQLite downgrade is intentionally skipped."""
    return None
