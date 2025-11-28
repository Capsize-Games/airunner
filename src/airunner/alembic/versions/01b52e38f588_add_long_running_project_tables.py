"""Add long-running project tables

Revision ID: 01b52e38f588
Revises: a2b5afa74dde
Create Date: 2025-11-28 04:54:23.299121

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from airunner.utils.db import add_table
from airunner.components.llm.long_running.data.project_state import (
    ProjectState,
    ProjectFeature,
    ProgressEntry,
    SessionState,
    DecisionMemory,
)
from airunner.components.llm.data.fine_tuned_model import FineTunedModel


# revision identifiers, used by Alembic.
revision: str = '01b52e38f588'
down_revision: Union[str, None] = 'a2b5afa74dde'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use add_table helper for SQLite compatibility
    # Order matters for foreign key dependencies
    
    # 1. First create tables with no FK dependencies
    add_table(FineTunedModel)
    add_table(ProjectState)  # ProjectState has no circular FK now
    
    # 2. Then create tables that depend on ProjectState
    add_table(ProjectFeature)
    add_table(SessionState)
    add_table(DecisionMemory)
    
    # 3. Finally create tables that depend on multiple tables
    add_table(ProgressEntry)


def downgrade() -> None:
    # Drop tables in reverse order of creation
    op.drop_table('progress_entries')
    op.drop_table('decision_memories')
    op.drop_table('session_states')
    op.drop_table('project_features')
    op.drop_table('project_states')
    op.drop_table('fine_tuned_models')
