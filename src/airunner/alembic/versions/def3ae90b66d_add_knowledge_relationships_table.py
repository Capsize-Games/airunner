"""add knowledge relationships table

Revision ID: def3ae90b66d
Revises: 500b6c395d38
Create Date: 2025-10-28 13:23:15.005536

"""

from typing import Sequence, Union

from airunner.utils.db import add_table, drop_table
from airunner.components.knowledge.data.knowledge_relationship import (
    KnowledgeRelationship,
)


# revision identifiers, used by Alembic.
revision: str = "def3ae90b66d"
down_revision: Union[str, None] = "500b6c395d38"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create knowledge_relationships table using helper for validation
    add_table(KnowledgeRelationship)


def downgrade() -> None:
    # Drop knowledge_relationships table
    drop_table(KnowledgeRelationship)
