"""add companion session and turn tables

Revision ID: 910441db1456
Revises: 0f8b4e43d1c2
Create Date: 2026-09-13 20:45:00.000000

"""

from typing import Sequence, Union

from airunner_services.database.models.companion_session import (
    CompanionSession,
)
from airunner_services.database.models.companion_turn import CompanionTurn
from airunner_services.database.db import add_table, drop_table


# revision identifiers, used by Alembic.
revision: str = "910441db1456"
down_revision: Union[str, None] = "0f8b4e43d1c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Additive only (release issue B02): neither table existed before, so
    # this cannot lose or alter any existing record.
    add_table(CompanionSession)
    add_table(CompanionTurn)


def downgrade() -> None:
    # Reverse creation order: companion_turns references companion_sessions.
    drop_table(CompanionTurn)
    drop_table(CompanionSession)
