"""added playback and recording device fields to app settings

Revision ID: 64ca532067c9
Revises: b808bb218e22
Create Date: 2025-04-06 08:47:15.143515

"""

from typing import Sequence, Union

from airunner.data.models import SoundSettings
from airunner.utils.db import add_table, drop_table


# revision identifiers, used by Alembic.
revision: str = "64ca532067c9"
down_revision: Union[str, None] = "b808bb218e22"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_table(SoundSettings)


def downgrade() -> None:
    drop_table(SoundSettings)
