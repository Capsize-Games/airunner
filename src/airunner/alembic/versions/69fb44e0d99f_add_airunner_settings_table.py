"""add airunner_settings table

Revision ID: 69fb44e0d99f
Revises: 7a320f14497a
Create Date: 2025-06-03 05:15:23.177996

"""

from typing import Sequence, Union

from airunner.components.settings.data.airunner_settings import AIRunnerSettings
from airunner.components.llm.data.chatbot import Chatbot
from airunner.components.llm.data.llm_generator_settings import LLMGeneratorSettings
from airunner.utils.db import (
    add_table,
    drop_table,
    drop_column,
    drop_constraint,
    create_foreign_key,
)

# revision identifiers, used by Alembic.
revision: str = "69fb44e0d99f"
down_revision: Union[str, None] = "7a320f14497a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_table(AIRunnerSettings)
    create_foreign_key(
        Chatbot, "voice_settings", ["voice_id"], ["id"], constraint_name=None
    )
    drop_constraint(LLMGeneratorSettings, "current_chatbot_fkey", "foreignkey")
    drop_column(LLMGeneratorSettings, "current_chatbot")


def downgrade() -> None:
    drop_table(AIRunnerSettings)
