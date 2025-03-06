"""add zipcode, lat and long fields to users table

Revision ID: 3473f48885c9
Revises: 713878b6e38f
Create Date: 2025-02-10 09:55:20.784057

"""
from typing import Union

from alembic import op
from airunner.utils.db import column_exists
from airunner.data.models import User

revision: str = '3473f48885c9'
down_revision: Union[str, None] = '713878b6e38f'


NEW_COLUMNS = [
    "zipcode",
    "location_display_name",
    "latitude",
    "longitude",
    "temperature_unit",
    "wind_speed_unit",
    "precipitation_unit"
]


def upgrade() -> None:
    for col in NEW_COLUMNS:
        try:
            if not column_exists(User.__tablename__, col):
                op.add_column(User.__tablename__, getattr(User, col))
            else:
                print(f"Column '{col}' already exists, skipping add.")
        except Exception as e:
            print(e)

def downgrade() -> None:
    for col in NEW_COLUMNS:
        try:
            op.drop_column(User.__tablename__, col)
        except Exception as e:
            print(e)