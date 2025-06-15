"""add detected language columsn to application settings'


Revision ID: 82e99b1a4ccc
Revises: 72977a42e2a2
Create Date: 2025-05-18 16:02:59.334823

"""

from typing import Sequence, Union

from airunner.components.settings.data.application_settings import ApplicationSettings
from airunner.utils.db import add_column, drop_column


# revision identifiers, used by Alembic.
revision: str = "82e99b1a4ccc"
down_revision: Union[str, None] = "72977a42e2a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column(ApplicationSettings, "detected_language")
    add_column(ApplicationSettings, "use_detected_language")


def downgrade() -> None:
    drop_column(ApplicationSettings, "detected_language")
    drop_column(ApplicationSettings, "use_detected_language")
