"""remove current conversation from llm generator settings

Revision ID: 201952ffe80a
Revises: b96406b64944
Create Date: 2025-05-27 12:13:11.496860

"""

from typing import Sequence, Union

from airunner.components.llm.data.llm_generator_settings import LLMGeneratorSettings
from airunner.utils.db import (
    add_column_with_fk,
    drop_column_with_fk,
)

import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "201952ffe80a"
down_revision: Union[str, None] = "b96406b64944"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column_with_fk(
        LLMGeneratorSettings,
        "current_chatbot",
        sa.Integer,
        "chatbots",
        "id",
        "current_chatbot_fkey",
    )
    # Only drop the column and its FK, do not attempt to drop constraints separately
    drop_column_with_fk(
        LLMGeneratorSettings,
        "current_conversation",
        "current_conversation_fkey",
    )


def downgrade() -> None:
    drop_column_with_fk(
        LLMGeneratorSettings,
        "current_chatbot",
        "current_chatbot_fkey",
    )
