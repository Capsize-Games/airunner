"""Make chatbot name distinct

Revision ID: bbd45baafc6f
Revises: 5dbbe8800572
Create Date: 2025-03-16 08:28:29.562179

"""
from typing import Union

from airunner.data.models import Chatbot
from airunner.utils.db import create_unique_constraint, drop_constraint


revision: str = 'bbd45baafc6f'
down_revision: Union[str, None] = '5dbbe8800572'


def upgrade() -> None:
    create_unique_constraint(
        Chatbot, 
        columns=['name'], 
        constraint_name="unique_chatbot_name"
    )


def downgrade() -> None:
    drop_constraint(
        Chatbot, 
        constraint_type="unique", 
        constraint_name="unique_chatbot_name"
    )