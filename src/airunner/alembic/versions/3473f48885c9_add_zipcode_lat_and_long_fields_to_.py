"""add zipcode, lat and long fields to users table

Revision ID: 3473f48885c9
Revises: 713878b6e38f
Create Date: 2025-02-10 09:55:20.784057

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = '3473f48885c9'
down_revision: Union[str, None] = '713878b6e38f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    columns_users = [col['name'] for col in inspector.get_columns('users')]

    try:
        if 'zipcode' not in columns_users:
            op.add_column('users', sa.Column('zipcode', sa.String(length=10), nullable=True))
        else:
            print("Column 'zipcode' already exists, skipping add.")
    except Exception as e:
        print(e)

    try:
        if 'location_display_name' not in columns_users:
            op.add_column('users', sa.Column('location_display_name', sa.String(), nullable=True))
        else:
            print("Column 'location_display_name' already exists, skipping add.")
    except Exception as e:
        print(e)

    try:
        if 'latitude' not in columns_users:
            op.add_column('users', sa.Column('latitude', sa.Float(), nullable=True))
        else:
            print("Column 'latitude' already exists, skipping add.")
    except Exception as e:
        print(e)

    try:
        if 'longitude' not in columns_users:
            op.add_column('users', sa.Column('longitude', sa.Float(), nullable=True))
        else:
            print("Column 'longitude' already exists, skipping add.")
    except Exception as e:
        print(e)

    try:
        if 'temperature_unit' not in columns_users:
            op.add_column('users', sa.Column('temperature_unit', sa.String(), nullable=False, server_default="fahrenheit"))
        else:
            print("Column 'temperature_unit' already exists, skipping add.")
    except Exception as e:
        print(e)

    try:
        if 'wind_speed_unit' not in columns_users:
            op.add_column('users', sa.Column('wind_speed_unit', sa.String(), nullable=False, server_default="mph"))
        else:
            print("Column 'wind_speed_unit' already exists, skipping add.")
    except Exception as e:
        print(e)

    try:
        if 'precipitation_unit' not in columns_users:
            op.add_column('users', sa.Column('precipitation_unit', sa.String(), nullable=False, server_default="inch"))
        else:
            print("Column 'precipitation_unit' already exists, skipping add.")
    except Exception as e:
        print(e)

def downgrade() -> None:
    try:
        op.drop_column('users', 'zipcode')
    except Exception as e:
        print(e)

    try:
        op.drop_column('users', 'location_display_name')
    except Exception as e:
        print(e)

    try:
        op.drop_column('users', 'latitude')
    except Exception as e:
        print(e)

    try:
        op.drop_column('users', 'longitude')
    except Exception as e:
        print(e)

    try:
        op.drop_column('users', 'temperature_unit')
    except Exception as e:
        print(e)

    try:
        op.drop_column('users', 'wind_speed_unit')
    except Exception as e:
        print(e)

    try:
        op.drop_column('users', 'precipitation_unit')
    except Exception as e:
        print(e)