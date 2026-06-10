"""remove retired nodegraph schema

Revision ID: b1c4d5e6f7a8
Revises: 810df6adb9db
Create Date: 2026-04-30 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1c4d5e6f7a8"
down_revision: Union[str, None] = "810df6adb9db"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _drop_columns_if_present(
    table_name: str,
    column_names: tuple[str, ...],
) -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return
    existing = {column["name"] for column in inspector.get_columns(table_name)}
    targets = [name for name in column_names if name in existing]
    if not targets:
        return
    recreate = "auto"
    with op.batch_alter_table(table_name, recreate=recreate) as batch_op:
        for name in targets:
            batch_op.drop_column(name)


def _drop_table_if_present(table_name: str) -> None:
    if _has_table(table_name):
        op.drop_table(table_name)


def upgrade() -> None:
    _drop_columns_if_present(
        "application_settings",
        (
            "nodegraph_zoom",
            "nodegraph_center_x",
            "nodegraph_center_y",
        ),
    )
    for table_name in (
        "workflow_run_events",
        "workflow_runs",
        "workflow_connections",
        "workflow_nodes",
        "workflows",
    ):
        _drop_table_if_present(table_name)


def downgrade() -> None:
    """Nodegraph has been removed and is not restored on downgrade."""
    return None
