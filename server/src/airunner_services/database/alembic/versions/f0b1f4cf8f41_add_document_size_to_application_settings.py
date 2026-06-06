"""add document size columns to application settings

Revision ID: f0b1f4cf8f41
Revises: f480bbc9acdb
Create Date: 2026-05-22 09:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
from airunner_services.database.db.column import add_column
from airunner_services.database.models.application_settings import (
    ApplicationSettings,
)

# revision identifiers, used by Alembic.
revision: str = "f0b1f4cf8f41"
down_revision: Union[str, None] = "f480bbc9acdb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column(ApplicationSettings, "document_width")
    add_column(ApplicationSettings, "document_height")


def downgrade() -> None:
    op.drop_column("application_settings", "document_height")
    op.drop_column("application_settings", "document_width")
