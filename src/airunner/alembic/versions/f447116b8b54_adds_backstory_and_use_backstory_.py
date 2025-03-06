"""Adds backstory and use_backstory columns to chatbot

Revision ID: f447116b8b54
Revises: 6c6cf295a892
Create Date: 2025-02-20 06:22:03.824057

"""
from typing import Union

from airunner.data.models import Chatbot
from airunner.utils.db import add_columns, drop_columns

revision: str = 'f447116b8b54'
down_revision: Union[str, None] = '6c6cf295a892'


def upgrade() -> None:
    add_columns(Chatbot, ['backstory', 'use_backstory'])
    
def downgrade() -> None:
    drop_columns(Chatbot, ['backstory', 'use_backstory'])
