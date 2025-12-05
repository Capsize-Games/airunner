"""add_dpm_pp_2m_sde_flow_scheduler

Revision ID: 7ea763b0785e
Revises: cec9a0a236f2
Create Date: 2025-12-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from airunner.enums import Scheduler


# revision identifiers, used by Alembic.
revision: str = '7ea763b0785e'
down_revision: Union[str, None] = 'cec9a0a236f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add DPM++ 2M SDE (Flow) scheduler for Z-Image and FLUX models."""
    connection = op.get_bind()
    
    # Check if scheduler already exists
    result = connection.execute(
        sa.text("SELECT id FROM schedulers WHERE display_name = :name"),
        {"name": Scheduler.FLOW_MATCH_DPM_PP_2M_SDE.value}
    ).fetchone()
    
    if result is None:
        connection.execute(
            sa.text(
                "INSERT INTO schedulers (display_name, name) VALUES (:display_name, :name)"
            ),
            {
                "display_name": Scheduler.FLOW_MATCH_DPM_PP_2M_SDE.value,
                "name": "FlowMatchEulerDiscreteScheduler",
            }
        )


def downgrade() -> None:
    """Remove DPM++ 2M SDE (Flow) scheduler."""
    connection = op.get_bind()
    connection.execute(
        sa.text("DELETE FROM schedulers WHERE display_name = :name"),
        {"name": Scheduler.FLOW_MATCH_DPM_PP_2M_SDE.value}
    )