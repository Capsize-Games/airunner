"""Modify latest columns

Revision ID: c81d3ee091da
Revises: 2efcc1665030
Create Date: 2025-04-21 06:26:56.618790

"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

from airunner.utils.db import (
    drop_constraint,
    add_column_with_fk,
    drop_column,
    safe_alter_column,
)
from airunner.data.models import (
    Chatbot,
    WorkflowConnection,
    WorkflowNode,
    Workflow,
)

# revision identifiers, used by Alembic.
revision: str = "c81d3ee091da"
down_revision: Union[str, None] = "2efcc1665030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def constraint_exists(conn, table_name, constraint_name):
    inspector = inspect(conn)
    constraints = inspector.get_unique_constraints(table_name)
    for constraint in constraints:
        if constraint["name"] == constraint_name:
            return True
    return False


def upgrade() -> None:
    # First try to drop any stale temporary tables that might exist
    try:
        op.execute("DROP TABLE IF EXISTS _alembic_tmp_chatbots")
    except Exception:
        pass

    # Check if the constraint exists before trying to drop it
    connection = op.get_bind()
    constraint_name = "uq_chatbots_voice_id"

    if constraint_exists(connection, "chatbots", constraint_name):
        # Then proceed with the constraint drop
        with op.batch_alter_table("chatbots", recreate="always") as batch_op:
            batch_op.drop_constraint(constraint_name, type_="unique")

    # Add columns with nullable=True to avoid NOT NULL constraint errors
    with op.batch_alter_table("workflow_connections") as batch_op:
        batch_op.add_column(
            sa.Column("output_port_name", sa.String(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("input_port_name", sa.String(), nullable=True)
        )

    # Use batch operations for foreign keys in SQLite
    with op.batch_alter_table("workflow_connections") as batch_op:
        batch_op.create_foreign_key(
            "fk_workflow_conn_output_node_id",
            "workflow_nodes",
            ["output_node_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_workflow_conn_workflow_id",
            "workflows",
            ["workflow_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_workflow_conn_input_node_id",
            "workflow_nodes",
            ["input_node_id"],
            ["id"],
        )

    # Drop columns
    drop_column(
        WorkflowConnection,
        "input_port",
    )
    drop_column(
        WorkflowConnection,
        "output_port",
    )

    # Use batch operations for foreign keys in SQLite
    with op.batch_alter_table("workflow_nodes") as batch_op:
        batch_op.create_foreign_key(
            "fk_workflow_node_workflow_id",
            "workflows",
            ["workflow_id"],
            ["id"],
        )

    drop_column(WorkflowNode, "subworkflow_id")
    drop_column(WorkflowNode, "is_subworkflow")
    drop_column(Workflow, "position_data")


def downgrade() -> None:
    drop_constraint(WorkflowNode, "fk_workflow_node_workflow_id")
    drop_constraint(WorkflowConnection, "fk_workflow_conn_workflow_id")
    drop_constraint(WorkflowConnection, "fk_workflow_conn_input_node_id")
    drop_constraint(WorkflowConnection, "fk_workflow_conn_output_node_id")
    drop_column(WorkflowConnection, "input_port_name")
    drop_column(WorkflowConnection, "output_port_name")
