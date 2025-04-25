"""added rag_settings table

Revision ID: 2d372e78d20b
Revises: ee56e41aa8cb
Create Date: 2025-04-25 08:18:39.618669

"""

from typing import Sequence, Union

from airunner.data.models.rag_settings import RAGSettings
from airunner.utils.db import add_table, drop_table


# revision identifiers, used by Alembic.
revision: str = "2d372e78d20b"
down_revision: Union[str, None] = "ee56e41aa8cb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_table(RAGSettings)


def downgrade() -> None:
    drop_table(RAGSettings)
