"""add age restriction column to application settings'


Revision ID: 32782f73752d
Revises: 1ca474ca1d8f
Create Date: 2025-05-21 23:58:42.539763

"""

from typing import Sequence, Union

from airunner.components.settings.data.application_settings import ApplicationSettings
from airunner.utils.db import add_column, drop_column


# revision identifiers, used by Alembic.
revision: str = "32782f73752d"
down_revision: Union[str, None] = "1ca474ca1d8f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column(ApplicationSettings, "age_agreement_checked")


def downgrade() -> None:
    drop_column(ApplicationSettings, "age_agreement_checked")
