"""Add enabled and trigger_words columns to lora table

Revision ID: add_lora_columns
Revises: f480bbc9acdb
Create Date: 2025-12-01

"""
from typing import Sequence, Union


from airunner_services.database.db.column import add_column, column_exists

# revision identifiers, used by Alembic.
revision: str = "add_lora_columns"
down_revision: Union[str, None] = "f0b1f4cf8f41"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from airunner_services.database.models.lora import Lora

    if not column_exists(Lora, "enabled"):
        add_column(Lora, "enabled")
    if not column_exists(Lora, "trigger_words"):
        add_column(Lora, "trigger_words")


def downgrade() -> None:
    from airunner_services.database.models.lora import Lora

    from airunner_services.database.db.column import drop_column

    if column_exists(Lora, "enabled"):
        drop_column(Lora, "enabled")
    if column_exists(Lora, "trigger_words"):
        drop_column(Lora, "trigger_words")
