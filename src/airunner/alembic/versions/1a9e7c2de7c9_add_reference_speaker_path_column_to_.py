"""add reference_speaker_path column to openvoicesettings

Revision ID: 1a9e7c2de7c9
Revises: 449cbcdca2c4
Create Date: 2025-05-15 16:36:18.412293

"""

from typing import Sequence, Union

from airunner.components.tts.data.models.openvoice_settings import OpenVoiceSettings
from airunner.utils.db import add_column, drop_column


# revision identifiers, used by Alembic.
revision: str = "1a9e7c2de7c9"
down_revision: Union[str, None] = "449cbcdca2c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column(OpenVoiceSettings, "reference_speaker_path")


def downgrade() -> None:
    drop_column(OpenVoiceSettings, "reference_speaker_path")
