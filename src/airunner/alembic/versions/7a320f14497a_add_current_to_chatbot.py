"""add current to chatbot

Revision ID: 7a320f14497a
Revises: 201952ffe80a
Create Date: 2025-05-27 14:21:23.661514

"""

from typing import Sequence, Union

from airunner.components.llm.data.chatbot import Chatbot
from airunner.utils.db import add_column, drop_column


# revision identifiers, used by Alembic.
revision: str = "7a320f14497a"
down_revision: Union[str, None] = "201952ffe80a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column(Chatbot, "current")


def downgrade() -> None:
    drop_column(Chatbot, "current")
