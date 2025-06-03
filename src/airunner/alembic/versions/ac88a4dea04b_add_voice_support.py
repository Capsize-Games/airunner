"""add voice support

Revision ID: ac88a4dea04b
Revises: 986e262645eb
Create Date: 2025-04-02 05:20:25.495089

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

from airunner.utils.db import (
    add_table,
    add_column,
    drop_table,
    drop_column,
    create_unique_constraint,
    drop_constraint,
)
from airunner.data.models import VoiceSettings, Chatbot


# revision identifiers, used by Alembic.
revision: str = "ac88a4dea04b"
down_revision: Union[str, None] = "986e262645eb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_table(VoiceSettings)
    add_column(Chatbot, "voice_id")
    create_unique_constraint(Chatbot, ["voice_id"], "uq_chatbots_voice_id")


def downgrade() -> None:
    # Check if the constraint exists before trying to drop it
    connection = op.get_bind()
    constraint_name = "uq_chatbots_voice_id"
    inspector = inspect(connection)
    constraints = inspector.get_unique_constraints("chatbots")
    if any(constraint["name"] == constraint_name for constraint in constraints):
        drop_constraint(Chatbot, "uq_chatbots_voice_id")
    drop_column(Chatbot, "voice_id")
    drop_table(VoiceSettings)
