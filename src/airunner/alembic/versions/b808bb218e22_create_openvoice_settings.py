"""create openvoice settings

Revision ID: b808bb218e22
Revises: 2d6569089de6
Create Date: 2025-04-02 09:16:55.969998

"""

from typing import Sequence, Union

from airunner.data.models.openvoice_settings import OpenVoiceSettings
from airunner.utils.db import add_table, drop_table


# revision identifiers, used by Alembic.
revision: str = "b808bb218e22"
down_revision: Union[str, None] = "2d6569089de6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_table(OpenVoiceSettings)


def downgrade() -> None:
    drop_table(OpenVoiceSettings)
