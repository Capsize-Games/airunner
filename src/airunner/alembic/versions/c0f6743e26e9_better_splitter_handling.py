"""Better splitter handling'


Revision ID: c0f6743e26e9
Revises: 7fb526dc074c
Create Date: 2025-03-11 10:02:25.695702

"""
from typing import Union
from airunner.utils.db import drop_table

# revision identifiers, used by Alembic.
revision: str = 'c0f6743e26e9'
down_revision: Union[str, None] = '7fb526dc074c'


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass