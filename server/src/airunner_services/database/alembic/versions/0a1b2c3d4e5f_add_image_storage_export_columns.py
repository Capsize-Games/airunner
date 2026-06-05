"""Add image storage/export columns to application_settings

Revision ID: 0a1b2c3d4e5f
Revises: 080398045849
Create Date: 2025-06-02 21:35:00.000000

"""

from typing import Sequence, Union

from airunner_services.database.models.application_settings import (
    ApplicationSettings,
)
from airunner_services.database.db import add_column

# revision identifiers, used by Alembic.
revision: str = "0a1b2c3d4e5f"
down_revision: Union[str, None] = "080398045849"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column(ApplicationSettings, "store_images_in_db")
    add_column(ApplicationSettings, "store_images_locally")
    add_column(ApplicationSettings, "image_export_folder")
    add_column(ApplicationSettings, "metadata_export_flags")


def downgrade() -> None:
    from airunner_services.database.db import drop_column

    drop_column(ApplicationSettings, "store_images_in_db")
    drop_column(ApplicationSettings, "store_images_locally")
    drop_column(ApplicationSettings, "image_export_folder")
    drop_column(ApplicationSettings, "metadata_export_flags")
