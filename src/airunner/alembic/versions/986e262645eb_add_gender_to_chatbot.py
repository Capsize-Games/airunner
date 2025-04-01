"""add gender to chatbot

Revision ID: 986e262645eb
Revises: 16a14e141cc8
Create Date: 2025-04-01 14:31:11.689080

"""
from typing import Sequence, Union

from airunner.data.models import Chatbot
from airunner.utils.db import add_column, drop_column


# revision identifiers, used by Alembic.
revision: str = '986e262645eb'
down_revision: Union[str, None] = '16a14e141cc8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column(Chatbot, "gender")


def downgrade() -> None:
    drop_column(Chatbot, "gender")