"""add use_weather_prompt to chatbot

Revision ID: 9cbb06f7c97f
Revises: 7802f91665d9
Create Date: 2025-03-04 10:02:18.969491

"""
from typing import Union

import sqlalchemy as sa
from airunner.utils.db import add_column, drop_column
from airunner.data.models import Chatbot


# revision identifiers, used by Alembic.
revision: str = '9cbb06f7c97f'
down_revision: Union[str, None] = '7802f91665d9'


def upgrade() -> None:
    add_column(Chatbot, sa.Column('use_weather_prompt', sa.Boolean(), nullable=True))


def downgrade() -> None:
    drop_column(Chatbot, 'use_weather_prompt')
