"""Add openai_api_key column to application_settings

Revision ID: add_openai_api_key
Revises: add_privacy_consent
Create Date: 2025-12-02

"""
from typing import Sequence, Union

from airunner_services.database.db.column import add_column, column_exists

# revision identifiers, used by Alembic.
revision: str = "add_openai_api_key"
down_revision: Union[str, None] = "add_privacy_consent"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from airunner_services.database.models.application_settings import (
        ApplicationSettings,
    )

    if not column_exists(ApplicationSettings, "openai_api_key"):
        add_column(ApplicationSettings, "openai_api_key")


def downgrade() -> None:
    from airunner_services.database.models.application_settings import (
        ApplicationSettings,
    )

    from airunner_services.database.db.column import drop_column

    if column_exists(ApplicationSettings, "openai_api_key"):
        drop_column(ApplicationSettings, "openai_api_key")
