"""remove nsfw

Revision ID: c42b9a3d807a
Revises: 65aa37e4593f
Create Date: 2025-11-10 11:28:53.714054

"""

from typing import Sequence, Union

from airunner.components.settings.data.application_settings import (
    ApplicationSettings,
)
from airunner.utils.db.column import drop_column


# revision identifiers, used by Alembic.
revision: str = "c42b9a3d807a"
down_revision: Union[str, None] = "65aa37e4593f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    drop_column(ApplicationSettings, "show_nsfw_warning")
    drop_column(ApplicationSettings, "nsfw_filter")


def downgrade() -> None:
    pass
