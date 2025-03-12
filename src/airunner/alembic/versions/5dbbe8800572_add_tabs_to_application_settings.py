"""Add tabs to application settings

Revision ID: 5dbbe8800572
Revises: c0f6743e26e9
Create Date: 2025-03-12 02:50:18.985375

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from airunner.data.models import ApplicationSettings
from airunner.utils.db import add_column, drop_column


# revision identifiers, used by Alembic.
revision: str = '5dbbe8800572'
down_revision: Union[str, None] = 'c0f6743e26e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column(ApplicationSettings, "tabs")
    settings = ApplicationSettings.objects.first()
    ApplicationSettings.objects.update(
        settings.id,
        tabs=ApplicationSettings.tabs.default.arg
    )


def downgrade() -> None:
    drop_column(ApplicationSettings, "tabs")