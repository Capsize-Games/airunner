"""add companion jobs table

Revision ID: 3beaa16d79c8
Revises: eb1b28d1b87f
Create Date: 2026-10-08 00:00:00.000000

"""

from typing import Sequence, Union

from airunner_services.database.models.companion_job import CompanionJob
from airunner_services.database.db import add_table, drop_table

# revision identifiers, used by Alembic.
revision: str = "3beaa16d79c8"
down_revision: Union[str, None] = "eb1b28d1b87f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Additive only (release issue B06): this table did not exist
    # before, so this cannot lose or alter any existing record.
    add_table(CompanionJob)


def downgrade() -> None:
    drop_table(CompanionJob)
