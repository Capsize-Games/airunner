"""remove rate and volume from speech t5 settings

Revision ID: 1de875096dfc
Revises: f447116b8b54
Create Date: 2025-02-23 08:45:09.519557

"""
from typing import Union

from airunner.utils.db import drop_columns, add_columns
from airunner.data.models import SpeechT5Settings

revision: str = '1de875096dfc'
down_revision: Union[str, None] = 'f447116b8b54'


def upgrade() -> None:
    drop_columns(SpeechT5Settings, ['rate', 'volume'])


def downgrade() -> None:
    add_columns(SpeechT5Settings, ['rate', 'volume'])