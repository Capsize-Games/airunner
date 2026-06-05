"""Add weight column to lora table

Revision ID: add_lora_weight
Revises: add_lora_columns
Create Date: 2025-12-02

"""
from typing import Sequence, Union


from airunner_services.database.db.column import add_column, column_exists

# revision identifiers, used by Alembic.
revision: str = "add_lora_weight"
down_revision: Union[str, None] = "add_lora_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from airunner_services.database.models.lora import Lora

    if not column_exists(Lora, "weight"):
        add_column(Lora, "weight")


def downgrade() -> None:
    from airunner_services.database.models.lora import Lora

    from airunner_services.database.db.column import drop_column

    if column_exists(Lora, "weight"):
        drop_column(Lora, "weight")
