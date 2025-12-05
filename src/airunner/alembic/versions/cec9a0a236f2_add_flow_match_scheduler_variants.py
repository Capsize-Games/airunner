"""add_flow_match_scheduler_variants

Revision ID: cec9a0a236f2
Revises: d4184aabeff9
Create Date: 2025-12-04 13:03:19.430118

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from airunner.enums import Scheduler


# revision identifiers, used by Alembic.
revision: str = 'cec9a0a236f2'
down_revision: Union[str, None] = 'd4184aabeff9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# New flow-match scheduler variants to add
NEW_SCHEDULERS = [
    {
        "display_name": Scheduler.FLOW_MATCH_EULER_KARRAS.value,
        "name": "FlowMatchEulerDiscreteScheduler",  # Same class, different config
    },
    {
        "display_name": Scheduler.FLOW_MATCH_EULER_STOCHASTIC.value,
        "name": "FlowMatchEulerDiscreteScheduler",  # Same class, different config
    },
    {
        "display_name": Scheduler.FLOW_MATCH_HEUN.value,
        "name": "FlowMatchHeunDiscreteScheduler",
    },
    {
        "display_name": Scheduler.FLOW_MATCH_LCM.value,
        "name": "FlowMatchLCMScheduler",
    },
]


def upgrade() -> None:
    """Add new flow-match scheduler variants for Z-Image and FLUX."""
    # Check if schedulers already exist before inserting
    connection = op.get_bind()
    
    for scheduler in NEW_SCHEDULERS:
        # Check if scheduler exists
        result = connection.execute(
            sa.text("SELECT id FROM schedulers WHERE display_name = :name"),
            {"name": scheduler["display_name"]}
        ).fetchone()
        
        if result is None:
            # Insert the new scheduler
            connection.execute(
                sa.text(
                    "INSERT INTO schedulers (display_name, name) VALUES (:display_name, :name)"
                ),
                scheduler
            )


def downgrade() -> None:
    """Remove the flow-match scheduler variants."""
    connection = op.get_bind()
    
    for scheduler in NEW_SCHEDULERS:
        connection.execute(
            sa.text("DELETE FROM schedulers WHERE display_name = :name"),
            {"name": scheduler["display_name"]}
        )