"""add_flow_match_euler_scheduler

Revision ID: a2b5afa74dde
Revises: 20c05328cd3b
Create Date: 2025-11-27 19:00:33.862188

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from airunner.enums import Scheduler


# revision identifiers, used by Alembic.
revision: str = 'a2b5afa74dde'
down_revision: Union[str, None] = '20c05328cd3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add FlowMatchEulerDiscreteScheduler for FLUX and Z-Image models."""
    # Check if scheduler already exists
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT id FROM schedulers WHERE display_name = :name"),
        {"name": Scheduler.FLOW_MATCH_EULER.value}
    ).fetchone()
    
    if result is None:
        # Insert the new scheduler
        conn.execute(
            sa.text(
                "INSERT INTO schedulers (display_name, name) VALUES (:display_name, :name)"
            ),
            {
                "display_name": Scheduler.FLOW_MATCH_EULER.value,
                "name": "FlowMatchEulerDiscreteScheduler",
            }
        )


def downgrade() -> None:
    """Remove FlowMatchEulerDiscreteScheduler."""
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM schedulers WHERE display_name = :name"),
        {"name": Scheduler.FLOW_MATCH_EULER.value}
    )