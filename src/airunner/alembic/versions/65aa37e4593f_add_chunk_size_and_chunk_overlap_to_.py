"""Add chunk_size and chunk_overlap to RAGSettings

Revision ID: 65aa37e4593f
Revises: 4cd9977eb573
Create Date: 2025-11-04 11:50:56.868000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from airunner.utils.db import add_column, drop_column
from airunner.components.llm.data.rag_settings import RAGSettings


# revision identifiers, used by Alembic.
revision: str = "65aa37e4593f"
down_revision: Union[str, None] = "4cd9977eb573"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add chunk_size and chunk_overlap columns to RAG settings
    add_column(RAGSettings, "chunk_size")
    add_column(RAGSettings, "chunk_overlap")


def downgrade() -> None:
    # Remove chunk_size and chunk_overlap columns from RAG settings
    drop_column(RAGSettings, "chunk_overlap")
    drop_column(RAGSettings, "chunk_size")
