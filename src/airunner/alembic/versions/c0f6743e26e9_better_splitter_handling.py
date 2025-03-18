"""Better splitter handling'


Revision ID: c0f6743e26e9
Revises: 7fb526dc074c
Create Date: 2025-03-11 10:02:25.695702

"""
from typing import Union
from airunner.utils.db import add_table, drop_table
from airunner.data.models import SplitterSetting

# revision identifiers, used by Alembic.
revision: str = 'c0f6743e26e9'
down_revision: Union[str, None] = '7fb526dc074c'


def upgrade() -> None:
    add_table(SplitterSetting)


def downgrade() -> None:
    drop_table(SplitterSetting)
