"""Add privacy_service_consent column to application_settings

Revision ID: add_privacy_consent
Revises: add_embedding_columns
Create Date: 2025-12-02

"""

from typing import Sequence, Union

from airunner_services.database.db.column import add_column, column_exists

# revision identifiers, used by Alembic.
revision: str = "add_privacy_consent"
down_revision: Union[str, None] = "add_embedding_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from airunner_services.database.models.application_settings import (
        ApplicationSettings,
    )

    if not column_exists(ApplicationSettings, "privacy_service_consent"):
        add_column(ApplicationSettings, "privacy_service_consent")


def downgrade() -> None:
    from airunner_services.database.models.application_settings import (
        ApplicationSettings,
    )

    from airunner_services.database.db.column import drop_column

    if column_exists(ApplicationSettings, "privacy_service_consent"):
        drop_column(ApplicationSettings, "privacy_service_consent")
