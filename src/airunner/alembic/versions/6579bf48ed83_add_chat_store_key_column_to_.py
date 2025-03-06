"""add chat_store_key column to Conversation table

Revision ID: 6579bf48ed83
Revises: c2c5d4cd4b80
Create Date: 2025-02-14 02:05:31.854218
"""
from typing import Union
import sqlalchemy as sa
from airunner.data.models import Conversation
from airunner.utils.db import add_columns, drop_columns

revision: str = '6579bf48ed83'
down_revision: Union[str, None] = 'c2c5d4cd4b80'

NEW_COLUMNS = [
    "key",
    "value"
]

def upgrade() -> None:
    add_columns(Conversation, NEW_COLUMNS)

def downgrade() -> None:
    drop_columns(Conversation, NEW_COLUMNS)