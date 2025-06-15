"""add language settings

Revision ID: cd69b4cecaed
Revises: 82e99b1a4ccc
Create Date: 2025-05-19 08:45:28.265195

"""

from typing import Sequence, Union

from airunner.components.settings.data.language_settings import LanguageSettings
from airunner.utils.db import add_table, drop_table


# revision identifiers, used by Alembic.
revision: str = "cd69b4cecaed"
down_revision: Union[str, None] = "82e99b1a4ccc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_table(LanguageSettings)


def downgrade() -> None:
    drop_table(LanguageSettings)
