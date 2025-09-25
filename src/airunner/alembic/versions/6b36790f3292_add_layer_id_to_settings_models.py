"""add_layer_id_to_settings_models

Revision ID: 6b36790f3292
Revises: b5f6cf56def4
Create Date: 2025-09-24 12:59:37.090166

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from airunner.utils.db.column import add_column, drop_column
from airunner.utils.db.foreign_key import create_foreign_key
from airunner.components.art.data.drawingpad_settings import DrawingPadSettings
from airunner.components.art.data.controlnet_settings import ControlnetSettings
from airunner.components.art.data.image_to_image_settings import (
    ImageToImageSettings,
)
from airunner.components.art.data.outpaint_settings import OutpaintSettings
from airunner.components.art.data.brush_settings import BrushSettings
from airunner.components.art.data.metadata_settings import MetadataSettings


# revision identifiers, used by Alembic.
revision: str = "6b36790f3292"
down_revision: Union[str, None] = "b5f6cf56def4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add layer_id foreign key columns to settings models."""
    # List of settings models that should be layer-specific
    settings_models = [
        DrawingPadSettings,
        ControlnetSettings,
        ImageToImageSettings,
        OutpaintSettings,
        BrushSettings,
        MetadataSettings,
    ]

    for model in settings_models:
        # Add layer_id column with batch operation for SQLite compatibility
        with op.batch_alter_table(
            model.__tablename__, recreate="always"
        ) as batch_op:
            # Add the layer_id column (nullable for existing records)
            batch_op.add_column(
                sa.Column("layer_id", sa.Integer, nullable=True)
            )

            # Add foreign key constraint
            batch_op.create_foreign_key(
                f"fk_{model.__tablename__}_layer_id",
                "canvas_layer",
                ["layer_id"],
                ["id"],
                ondelete="CASCADE",
            )


def downgrade() -> None:
    """Remove layer_id foreign key columns from settings models."""
    settings_models = [
        DrawingPadSettings,
        ControlnetSettings,
        ImageToImageSettings,
        OutpaintSettings,
        BrushSettings,
        MetadataSettings,
    ]

    for model in settings_models:
        with op.batch_alter_table(
            model.__tablename__, recreate="always"
        ) as batch_op:
            # Drop foreign key constraint first
            batch_op.drop_constraint(
                f"fk_{model.__tablename__}_layer_id", type_="foreignkey"
            )

            # Drop the layer_id column
            batch_op.drop_column("layer_id")
