"""Add dark_mode_enabled_db column to application_settings

Revision ID: add_dark_mode_enabled
Revises: add_openai_api_key
Create Date: 2025-12-02

"""

from typing import Sequence, Union

from airunner_services.database.db.column import add_column, column_exists

# revision identifiers, used by Alembic.
revision: str = "add_dark_mode_enabled"
down_revision: Union[str, None] = "add_openai_api_key"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from airunner_services.database.models.application_settings import (
        ApplicationSettings,
    )

    if not column_exists(ApplicationSettings, "dark_mode_enabled_db"):
        add_column(ApplicationSettings, "dark_mode_enabled_db")


def downgrade() -> None:
    from airunner_services.database.models.application_settings import (
        ApplicationSettings,
    )

    from airunner_services.database.db.column import drop_column

    if column_exists(ApplicationSettings, "dark_mode_enabled_db"):
        drop_column(ApplicationSettings, "dark_mode_enabled_db")
