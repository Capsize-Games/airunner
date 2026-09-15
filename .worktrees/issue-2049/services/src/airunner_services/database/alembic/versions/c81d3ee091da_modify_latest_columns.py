"""Modify latest columns

Revision ID: c81d3ee091da
Revises: 2efcc1665030
Create Date: 2025-04-21 06:26:56.618790

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "c81d3ee091da"
down_revision: Union[str, None] = "2efcc1665030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Retired with nodegraph removal; kept for migration continuity."""
    return None


def downgrade() -> None:
    """Retired with nodegraph removal; kept for migration continuity."""
    return None
