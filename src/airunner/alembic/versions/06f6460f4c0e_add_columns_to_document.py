"""add columns to Document'


Revision ID: 06f6460f4c0e
Revises: 9d76c1e50d8f
Create Date: 2025-10-08 08:12:27.302592

"""

from typing import Sequence, Union

from airunner.components.documents.data.models.document import Document
from airunner.utils.db.column import add_column, drop_column


# revision identifiers, used by Alembic.
revision: str = "06f6460f4c0e"
down_revision: Union[str, None] = "9d76c1e50d8f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column(Document, "file_hash")
    add_column(Document, "indexed_at")
    add_column(Document, "file_size")


def downgrade() -> None:
    drop_column(Document, "file_size")
    drop_column(Document, "indexed_at")
    drop_column(Document, "file_hash")
