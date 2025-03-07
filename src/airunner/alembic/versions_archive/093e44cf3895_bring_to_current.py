"""bring to current

Revision ID: 093e44cf3895
Revises: 9fab4d94d3e1
Create Date: 2025-03-06 16:26:10.390178

"""
from typing import Union

import sqlalchemy as sa
from airunner.utils.db import add_columns, safe_alter_column, drop_columns
from airunner.data.models import Chatbot, User, SpeechT5Settings


revision: str = '093e44cf3895'
down_revision: Union[str, None] = '9fab4d94d3e1'


def upgrade() -> None:
    add_columns(Chatbot, [
        sa.Column('use_weather_prompt', sa.Boolean(), nullable=True)
    ])
    safe_alter_column(
        SpeechT5Settings, 
        'voice',
        existing_type=sa.VARCHAR(),
        nullable=True,
        existing_server_default=sa.text("'US Male'")
    )
    add_columns(User, [
        sa.Column('zipcode', sa.String(), nullable=True),
        sa.Column('location_display_name', sa.String(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True)
    ])


def downgrade() -> None:
    drop_columns(User, ['zipcode', 'location_display_name', 'latitude', 'longitude'])
    safe_alter_column(
        SpeechT5Settings, 
        'voice',
        existing_type=sa.VARCHAR(),
        nullable=False,
        existing_server_default=sa.text("'US Male'")
    )
    drop_columns(Chatbot, ['use_weather_prompt'])