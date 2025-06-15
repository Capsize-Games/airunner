"""add documents

Revision ID: f8077817b00e
Revises: 69fb44e0d99f
Create Date: 2025-06-08 22:04:00.677480

"""

from typing import Sequence, Union

from airunner.components.documents.data.models.document import Document
from airunner.utils.db import add_table, drop_table


# revision identifiers, used by Alembic.
revision: str = "f8077817b00e"
down_revision: Union[str, None] = "69fb44e0d99f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_table(Document)


def downgrade() -> None:
    drop_table(Document)
