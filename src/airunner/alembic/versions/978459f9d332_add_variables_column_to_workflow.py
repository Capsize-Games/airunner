"""add variables column to workflow

Revision ID: 978459f9d332
Revises: c81d3ee091da
Create Date: 2025-04-21 07:43:56.722842

"""

from typing import Sequence, Union

import sqlalchemy as sa

from airunner.data.models import Workflow, WorkflowConnection
from airunner.utils.db import add_column, drop_column, alter_column


# revision identifiers, used by Alembic.
revision: str = "978459f9d332"
down_revision: Union[str, None] = "c81d3ee091da"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    alter_column(
        WorkflowConnection,
        WorkflowConnection.input_port_name,
        sa.Column(
            WorkflowConnection.input_port_name.name,
            WorkflowConnection.input_port_name.type,
            nullable=False,
        ),
    )
    alter_column(
        WorkflowConnection,
        WorkflowConnection.output_port_name,
        sa.Column(
            WorkflowConnection.output_port_name.name,
            WorkflowConnection.output_port_name.type,
            nullable=False,
        ),
    )
    add_column(Workflow, "variables")


def downgrade() -> None:
    drop_column(Workflow, "variables")
    alter_column(
        WorkflowConnection,
        WorkflowConnection.input_port_name,
        sa.Column(
            WorkflowConnection.input_port_name.name,
            WorkflowConnection.input_port_name.type,
            nullable=True,
        ),
    )
    alter_column(
        WorkflowConnection,
        WorkflowConnection.output_port_name,
        sa.Column(
            WorkflowConnection.output_port_name.name,
            WorkflowConnection.output_port_name.type,
            nullable=True,
        ),
    )
