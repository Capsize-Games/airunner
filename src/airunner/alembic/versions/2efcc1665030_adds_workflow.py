"""adds workflow

Revision ID: 2efcc1665030
Revises: 64ca532067c9
Create Date: 2025-04-19 16:48:15.515574

"""

from typing import Sequence, Union

from airunner.utils.db import add_table, drop_table
from airunner.data.models import Workflow, WorkflowNode, WorkflowConnection


# revision identifiers, used by Alembic.
revision: str = "2efcc1665030"
down_revision: Union[str, None] = "64ca532067c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_table(Workflow)
    add_table(WorkflowNode)
    add_table(WorkflowConnection)


def downgrade() -> None:
    drop_table(WorkflowConnection)
    drop_table(WorkflowNode)
    drop_table(Workflow)
