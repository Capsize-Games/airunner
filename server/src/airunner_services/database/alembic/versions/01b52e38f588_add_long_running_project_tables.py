"""Add long-running project tables

Revision ID: 01b52e38f588
Revises: a2b5afa74dde
Create Date: 2025-11-28 04:54:23.299121

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from airunner_services.database.db import add_table
from airunner_services.database.models.project_state import (
    ProjectState,
    ProjectFeature,
    ProgressEntry,
    SessionState,
    DecisionMemory,
)

# revision identifiers, used by Alembic.
revision: str = "01b52e38f588"
down_revision: Union[str, None] = "a2b5afa74dde"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use add_table helper for SQLite compatibility
    # Order matters for foreign key dependencies

    fine_tuned_models = type(
        "_FineTunedModelsTable",
        (),
        {
            "__tablename__": "fine_tuned_models",
            "__table__": sa.Table(
                "fine_tuned_models",
                sa.MetaData(),
                sa.Column(
                    "id", sa.Integer(), autoincrement=True, nullable=False
                ),
                sa.Column("name", sa.String(), nullable=False),
                sa.Column("adapter_path", sa.String(), nullable=True),
                sa.Column("date_added", sa.DateTime(), nullable=True),
                sa.Column("last_trained", sa.DateTime(), nullable=True),
                sa.Column("files_used", sa.JSON(), nullable=True),
                sa.Column("settings", sa.JSON(), nullable=True),
                sa.Column("tags", sa.JSON(), nullable=True),
                sa.PrimaryKeyConstraint("id"),
            ),
            "__table_args__": (sa.UniqueConstraint("name"),),
        },
    )

    # 1. First create tables with no FK dependencies
    add_table(fine_tuned_models)
    add_table(ProjectState)  # ProjectState has no circular FK now

    # 2. Then create tables that depend on ProjectState
    add_table(ProjectFeature)
    add_table(SessionState)
    add_table(DecisionMemory)

    # 3. Finally create tables that depend on multiple tables
    add_table(ProgressEntry)


def downgrade() -> None:
    # Drop tables in reverse order of creation
    op.drop_table("progress_entries")
    op.drop_table("decision_memories")
    op.drop_table("session_states")
    op.drop_table("project_features")
    op.drop_table("project_states")
    op.drop_table("fine_tuned_models")
