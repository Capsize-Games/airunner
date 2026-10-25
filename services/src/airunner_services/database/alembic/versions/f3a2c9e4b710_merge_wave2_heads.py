"""merge wave-2 heads into one linear head

Revision ID: f3a2c9e4b710
Revises: a7c93f2e1b4d, d951d2fd378d
Create Date: 2026-10-25 00:00:00.000000

Merge the two concurrent heads back into one linear head so
``alembic upgrade head`` is unambiguous again.

NOTE: an earlier audit listed five heads (48b1c0d3e4f5, 5a4d9d9e0b67,
b1c4d5e6f7a8 plus the two below). Those three are NOT heads: revision
``d2ab5f1c9a7e`` already merges them, so merging them again would
re-fork settled history and break upgrades from partial stamps.
Only the two true heads are merged here.
"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "f3a2c9e4b710"
down_revision: Union[Sequence[str], None] = (
    "a7c93f2e1b4d",
    "d951d2fd378d",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge heads; no schema change."""


def downgrade() -> None:
    """Merge heads; no schema change to revert."""
