"""Add theme_name column to application_settings

Revision ID: add_theme_name
Revises: add_dark_mode_enabled
Create Date: 2025-12-03

"""

from typing import Sequence, Union

from airunner_services.database.db.column import add_column, column_exists

# revision identifiers, used by Alembic.
revision: str = "add_theme_name"
down_revision: Union[str, None] = "add_dark_mode_enabled"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from airunner_services.database.models.application_settings import (
        ApplicationSettings,
    )

    if not column_exists(ApplicationSettings, "theme_name"):
        add_column(ApplicationSettings, "theme_name")


def downgrade() -> None:
    from airunner_services.database.models.application_settings import (
        ApplicationSettings,
    )

    from airunner_services.database.db.column import drop_column

    if column_exists(ApplicationSettings, "theme_name"):
        drop_column(ApplicationSettings, "theme_name")
