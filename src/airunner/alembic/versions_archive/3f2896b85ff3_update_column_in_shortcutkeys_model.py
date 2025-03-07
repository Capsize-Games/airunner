"""Update column in ShortcutKeys model

Revision ID: 3f2896b85ff3
Revises: f31260eb8751
Create Date: 2025-03-03 15:00:19.780194

"""
from typing import Union

import sqlalchemy as sa
from airunner.utils.db import alter_column
from airunner.data.models import ShortcutKeys

revision: str = '3f2896b85ff3'
down_revision: Union[str, None] = 'f31260eb8751'


def upgrade() -> None:
    alter_column(
        ShortcutKeys, 
        sa.Column('signal', sa.Integer(), nullable=False, server_default=''),
        sa.Column('signal', sa.String(), nullable=False, server_default='')
    )


def downgrade() -> None:
    alter_column(
        ShortcutKeys, 
        sa.Column('signal', sa.String(), nullable=False, server_default=''),
        sa.Column('signal', sa.Integer(), nullable=False, server_default='')
    )