"""add unit_system column to User

Revision ID: 68875bccab07
Revises: 5e03be0b5d05
Create Date: 2025-03-04 10:29:27.575449

"""
from typing import Union

from alembic import op
import sqlalchemy as sa
from airunner.utils.db import column_exists
from airunner.data.models import User

# revision identifiers, used by Alembic.
revision: str = '68875bccab07'
down_revision: Union[str, None] = '5e03be0b5d05'


def upgrade() -> None:
    # Add unit_system column if it doesn't exist
    if not column_exists(User, 'unit_system'):
        op.add_column('users', sa.Column('unit_system', sa.String(), nullable=True))
    
    if op.get_bind().dialect.name == 'sqlite':
        # Use batch operations for SQLite
        with op.batch_alter_table('users', recreate='always') as batch_op:
            batch_op.alter_column('username', existing_type=sa.String(), server_default='User', nullable=False)
    else:
        op.alter_column('users', 'username',
                        existing_type=sa.String(length=50),
                        nullable=False,
                        server_default='User')
    
    # Drop columns if they exist
    if column_exists(User, 'precipitation_unit'):
        op.drop_column('users', 'precipitation_unit')
    if column_exists(User, 'wind_speed_unit'):
        op.drop_column('users', 'wind_speed_unit')
    if column_exists(User, 'temperature_unit'):
        op.drop_column('users', 'temperature_unit')


def downgrade() -> None:
    # Add columns back if they don't exist
    if not column_exists(User, 'temperature_unit'):
        op.add_column('users', sa.Column('temperature_unit', sa.String(), nullable=True))
    if not column_exists(User, 'wind_speed_unit'):
        op.add_column('users', sa.Column('wind_speed_unit', sa.String(), nullable=True))
    if not column_exists(User, 'precipitation_unit'):
        op.add_column('users', sa.Column('precipitation_unit', sa.String(), nullable=True))
    
    if op.get_bind().dialect.name == 'sqlite':
        # Use batch operations for SQLite
        with op.batch_alter_table('users', recreate='always') as batch_op:
            batch_op.alter_column('username', existing_type=sa.String(), server_default=None, nullable=True)
    else:
        op.alter_column('users', 'username',
                        existing_type=sa.String(length=50),
                        nullable=True,
                        server_default=None)
    
    # Drop unit_system column if it exists
    if column_exists(User, 'unit_system'):
        op.drop_column('users', 'unit_system')