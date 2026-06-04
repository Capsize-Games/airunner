"""remove retired adapter schema

Revision ID: 0f8b4e43d1c2
Revises: 6b0f0f6c3e4a
Create Date: 2026-05-17 00:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union
from airunner_services.database.db.column import drop_column
from airunner_services.database.db.table import drop_table
from airunner_services.database.models import LLMGeneratorSettings
from airunner_services.database.models import GeneratorSettings
from airunner_services.database.models import MetadataSettings


revision: str = "0f8b4e43d1c2"
down_revision: Union[str, None] = "6b0f0f6c3e4a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop retired adapter, LoRA, and embedding schema."""
    drop_column(
        LLMGeneratorSettings,
        "enabled_adapters",
    )
    drop_column(
        GeneratorSettings,
        "lora_scale",
    )
    drop_column(
        MetadataSettings,
        "image_export_metadata_lora",
    )
    drop_column(
        MetadataSettings,
        "image_export_metadata_embeddings",
    )
    drop_table(None, "lora")
    drop_table(None, "embeddings")
    drop_table(None, "fine_tuned_models")


def downgrade() -> None:
    """Retired schema is not restored on downgrade."""
    return None