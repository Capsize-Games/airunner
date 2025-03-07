"""Adds voice column to speech_t5_settings table

Revision ID: f31260eb8751
Revises: 1de875096dfc
Create Date: 2025-02-23 09:49:55.536580

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

from airunner.enums import SpeechT5Voices

# revision identifiers, used by Alembic.
revision: str = 'f31260eb8751'
down_revision: Union[str, None] = '1de875096dfc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    columns_speech_t5_settings = [col['name'] for col in inspector.get_columns('speech_t5_settings')]

    try:
        if 'voice' not in columns_speech_t5_settings:
            op.add_column('speech_t5_settings', sa.Column(
                'voice', 
                sa.String(), 
                nullable=False, 
                server_default=SpeechT5Voices.US_MALE.value
            ))
        else:
            print("Column 'voice' already exists, skipping add.")
    except sa.exc.OperationalError as e:
        print("Error adding column 'voice': ", e)


def downgrade() -> None:
    try:
        op.drop_column('speech_t5_settings', 'voice')
    except Exception as e:
        print("Error dropping column 'voice': ", e)