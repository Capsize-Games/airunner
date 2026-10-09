"""add companion fact and narrative tables

Revision ID: eb1b28d1b87f
Revises: 910441db1456
Create Date: 2026-10-08 00:00:00.000000

"""

from typing import Sequence, Union

from airunner_services.database.models.companion_fact import CompanionFact
from airunner_services.database.models.companion_narrative import (
    CompanionNarrative,
)
from airunner_services.database.db import add_table, drop_table

# revision identifiers, used by Alembic.
revision: str = "eb1b28d1b87f"
down_revision: Union[str, None] = "910441db1456"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Additive only (release issue B03): neither table existed before,
    # so this cannot lose or alter any existing record. Existing
    # file/document knowledge tables are left untouched (B14 migrates
    # them); no vector index columns are added (B04's scope).
    add_table(CompanionFact)
    add_table(CompanionNarrative)


def downgrade() -> None:
    # Reverse creation order (no FK between the two tables; either
    # order would work, but keep the B02 convention anyway).
    drop_table(CompanionNarrative)
    drop_table(CompanionFact)
