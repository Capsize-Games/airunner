"""Adds summary column to conversations table

Revision ID: 6c6cf295a892
Revises: f3d84a9d5049
Create Date: 2025-02-19 02:33:21.496409

"""
from typing import Union

from airunner.utils.db import add_columns, drop_columns
from airunner.data.models import Conversation

revision: str = '6c6cf295a892'
down_revision: Union[str, None] = 'f3d84a9d5049'


def upgrade() -> None:
    add_columns(Conversation, ["summary", "user_data"])


def downgrade() -> None:
    drop_columns(Conversation, ["summary", "user_data"])