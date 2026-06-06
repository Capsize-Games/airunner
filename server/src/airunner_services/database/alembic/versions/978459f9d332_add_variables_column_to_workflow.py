"""add variables column to workflow

Revision ID: 978459f9d332
Revises: c81d3ee091da
Create Date: 2025-04-21 07:43:56.722842

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "978459f9d332"
down_revision: Union[str, None] = "c81d3ee091da"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Retired with nodegraph removal; kept for migration continuity."""
    return None


def downgrade() -> None:
    """Retired with nodegraph removal; kept for migration continuity."""
    return None
