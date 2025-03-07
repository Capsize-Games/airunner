"""Adds user_id, chatbot_name and user_name columns to conversation table

Revision ID: 2c12bfc33385
Revises: bd0a424f223d
Create Date: 2025-02-15 04:46:57.397764

"""
from typing import Union

from airunner.utils.db import add_columns, drop_columns
from airunner.data.models import Conversation

revision: str = '2c12bfc33385'
down_revision: Union[str, None] = 'bd0a424f223d'


def upgrade() -> None:
    add_columns(Conversation, ['user_id', 'chatbot_name', 'user_name', 'status'])

def downgrade() -> None:
    drop_columns(Conversation, ['user_id', 'chatbot_name', 'user_name', 'status'])