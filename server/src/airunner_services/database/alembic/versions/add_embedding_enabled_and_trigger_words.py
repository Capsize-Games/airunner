"""Add enabled and trigger_words columns to embeddings table

Revision ID: add_embedding_columns
Revises: add_lora_weight
Create Date: 2025-12-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from airunner_services.database.db.column import add_column, column_exists

# revision identifiers, used by Alembic.
revision: str = "add_embedding_columns"
down_revision: Union[str, None] = "add_lora_weight"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from airunner_services.database.models.embedding import Embedding

    if not column_exists(Embedding, "enabled"):
        add_column(Embedding, "enabled")
    if not column_exists(Embedding, "trigger_words"):
        add_column(Embedding, "trigger_words")


def downgrade() -> None:
    from airunner_services.database.models.embedding import Embedding

    from airunner_services.database.db.column import drop_column

    if column_exists(Embedding, "enabled"):
        drop_column(Embedding, "enabled")
    if column_exists(Embedding, "trigger_words"):
        drop_column(Embedding, "trigger_words")
