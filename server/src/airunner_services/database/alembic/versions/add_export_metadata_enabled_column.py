"""Add export_metadata_enabled column to application_settings

Revision ID: add_export_metadata_enabled
Revises: add_theme_name
Create Date: 2025-12-02

"""

from typing import Sequence, Union

from airunner_services.database.db.column import add_column, column_exists

# revision identifiers, used by Alembic.
revision: str = "add_export_metadata_enabled"
down_revision: Union[str, None] = "add_theme_name"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from airunner_services.database.models.application_settings import (
        ApplicationSettings,
    )

    if not column_exists(ApplicationSettings, "export_metadata_enabled"):
        add_column(ApplicationSettings, "export_metadata_enabled")


def downgrade() -> None:
    from airunner_services.database.models.application_settings import (
        ApplicationSettings,
    )

    from airunner_services.database.db.column import drop_column

    if column_exists(ApplicationSettings, "export_metadata_enabled"):
        drop_column(ApplicationSettings, "export_metadata_enabled")
