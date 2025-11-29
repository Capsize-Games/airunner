"""add llm tool and knowledge tables

Revision ID: eda751de4bed
Revises: 533e97f2b74c
Create Date: 2025-10-23 11:06:13.642804

NOTE: Knowledge tables (KnowledgeFact, ConversationSummary) were later removed
in migration f480bbc9acdb. The model classes have been deleted.
"""

from typing import Sequence, Union

from airunner.components.llm.data.llm_tool import LLMTool
from alembic import op
import sqlalchemy as sa
from airunner.utils.db import add_table, drop_table

# revision identifiers, used by Alembic.
revision: str = "eda751de4bed"
down_revision: Union[str, None] = "533e97f2b74c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add LLMTool table (still exists)
    add_table(LLMTool)
    
    # Create knowledge tables directly with raw SQL
    # (These will be dropped in migration f480bbc9acdb)
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()
    
    if "conversation_summaries" not in existing_tables:
        op.create_table(
            "conversation_summaries",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("conversation_id", sa.String(255), nullable=False),
            sa.Column("summary", sa.Text(), nullable=False),
            sa.Column("period_type", sa.String(50), default="session"),
            sa.Column("created_at", sa.DateTime()),
            sa.Column("message_count", sa.Integer(), default=0),
        )
    
    if "knowledge_facts" not in existing_tables:
        op.create_table(
            "knowledge_facts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("category", sa.String(100)),
            sa.Column("confidence", sa.Float(), default=1.0),
            sa.Column("source", sa.String(255)),
            sa.Column("created_at", sa.DateTime()),
            sa.Column("last_accessed", sa.DateTime()),
            sa.Column("access_count", sa.Integer(), default=0),
        )

    # Drop obsolete table
    drop_table(table_name="fine_tuned_models")


def downgrade() -> None:
    # Drop tables
    drop_table(LLMTool)
    
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()
    
    if "knowledge_facts" in existing_tables:
        op.drop_table("knowledge_facts")
    if "conversation_summaries" in existing_tables:
        op.drop_table("conversation_summaries")
