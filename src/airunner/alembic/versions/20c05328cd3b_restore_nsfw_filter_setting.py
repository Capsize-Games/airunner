"""restore_nsfw_filter_setting

Revision ID: 20c05328cd3b
Revises: c42b9a3d807a
Create Date: 2025-11-11 05:27:57.681114

"""
from typing import Sequence, Union

from airunner.utils.db import add_column
from airunner.components.settings.data.application_settings import ApplicationSettings


# revision identifiers, used by Alembic.
revision: str = '20c05328cd3b'
down_revision: Union[str, None] = 'c42b9a3d807a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add nsfw_filter column (default=True is defined in the model)
    add_column(ApplicationSettings, "nsfw_filter")


def downgrade() -> None:
    # CRITICAL: SQLite does not support DROP COLUMN directly
    # This would require table recreation. Manual intervention required.
    pass
