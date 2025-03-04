"""add use_weather_prompt to chatbot

Revision ID: 9cbb06f7c97f
Revises: 7802f91665d9
Create Date: 2025-03-04 10:02:18.969491

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = '9cbb06f7c97f'
down_revision: Union[str, None] = '7802f91665d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    columns = [col['name'] for col in inspector.get_columns('chatbots')]
    if 'use_weather_prompt' not in columns:
        op.add_column('chatbots', sa.Column('use_weather_prompt', sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column('chatbots', 'use_weather_prompt')
