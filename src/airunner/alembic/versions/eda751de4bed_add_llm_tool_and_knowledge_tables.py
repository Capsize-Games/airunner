"""add llm tool and knowledge tables

Revision ID: eda751de4bed
Revises: 533e97f2b74c
Create Date: 2025-10-23 11:06:13.642804

"""

from typing import Sequence, Union

from airunner.components.llm.data.llm_tool import LLMTool
from airunner.components.knowledge.data.models import (
    KnowledgeFact,
    ConversationSummary,
)
from alembic import op
from airunner.utils.db import add_table, drop_table

# revision identifiers, used by Alembic.
revision: str = "eda751de4bed"
down_revision: Union[str, None] = "533e97f2b74c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new tables
    add_table(ConversationSummary)
    add_table(KnowledgeFact)
    add_table(LLMTool)

    # Drop obsolete table
    drop_table(table_name="fine_tuned_models")


def downgrade() -> None:
    # Drop new tables
    drop_table(LLMTool)
    drop_table(KnowledgeFact)
    drop_table(ConversationSummary)

    # Note: We don't recreate fine_tuned_models as it's obsolete
    op.drop_index(
        op.f("ix_conversation_summaries_period_type"),
        table_name="conversation_summaries",
    )
    op.drop_index(
        op.f("ix_conversation_summaries_created_at"),
        table_name="conversation_summaries",
    )
    op.drop_index(
        op.f("ix_conversation_summaries_conversation_id"),
        table_name="conversation_summaries",
    )
    op.drop_table("conversation_summaries")
    # ### end Alembic commands ###
