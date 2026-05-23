"""add calendar tables

Revision ID: 04ea79f25b7a
Revises: 91e21ecaef23
Create Date: 2025-10-27 14:38:11.893120

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "04ea79f25b7a"
down_revision: Union[str, None] = "91e21ecaef23"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Retired with calendar removal; kept for migration continuity."""
    return None


def downgrade() -> None:
    """Retired with calendar removal; kept for migration continuity."""
    return None
