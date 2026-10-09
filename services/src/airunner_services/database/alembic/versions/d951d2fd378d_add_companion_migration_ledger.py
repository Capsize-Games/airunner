"""add companion migration ledger table

Revision ID: d951d2fd378d
Revises: 3beaa16d79c8
Create Date: 2026-10-09 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

from airunner_services.llm.companion.migration_ledger import (
    MIGRATION_LEDGER_TABLE,
    MIGRATION_METADATA,
)

# revision identifiers, used by Alembic.
revision: str = "d951d2fd378d"
down_revision: Union[str, None] = "3beaa16d79c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Additive only (release issue B14): this table is new, so this
    # cannot lose or alter any existing record. The table definition
    # lives in migration_ledger.py, the single schema source shared
    # with the migration runner and its regression tests.
    MIGRATION_METADATA.create_all(
        bind=op.get_bind(),
        tables=[MIGRATION_LEDGER_TABLE],
        checkfirst=True,
    )


def downgrade() -> None:
    op.drop_table(MIGRATION_LEDGER_TABLE.name)
