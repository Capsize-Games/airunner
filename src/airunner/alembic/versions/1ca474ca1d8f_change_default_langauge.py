"""change default langauge

Revision ID: 1ca474ca1d8f
Revises: cd69b4cecaed
Create Date: 2025-05-19 15:39:54.457934

"""

from typing import Sequence, Union

from airunner.components.tts.data.models.openvoice_settings import OpenVoiceSettings
from airunner.utils.db.column import safe_alter_column

# revision identifiers, used by Alembic.
revision: str = "1ca474ca1d8f"
down_revision: Union[str, None] = "cd69b4cecaed"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    safe_alter_column(
        OpenVoiceSettings,
        OpenVoiceSettings.language,
        OpenVoiceSettings.language.copy(default="EN"),
    )

    openvoice_settings = OpenVoiceSettings.objects.all()
    for setting in openvoice_settings:
        if setting.language == "EN_NEWEST":
            OpenVoiceSettings.objects.update(
                setting.id,
                language="EN",
            )


def downgrade() -> None:
    safe_alter_column(
        OpenVoiceSettings,
        OpenVoiceSettings.language,
        OpenVoiceSettings.language.copy(default="EN"),
    )
