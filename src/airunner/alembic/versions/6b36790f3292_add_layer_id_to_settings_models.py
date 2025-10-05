"""add_layer_id_to_settings_models

Revision ID: 6b36790f3292
Revises: b5f6cf56def4
Create Date: 2025-09-24 12:59:37.090166

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from airunner.components.art.data.drawingpad_settings import DrawingPadSettings
from airunner.components.art.data.controlnet_settings import ControlnetSettings
from airunner.components.art.data.image_to_image_settings import (
    ImageToImageSettings,
)
from airunner.components.art.data.outpaint_settings import OutpaintSettings


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
    ]
    # Get inspector to check existing schema so this migration is idempotent
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for model in settings_models:
        table_name = model.__tablename__

        # If the column already exists, skip modifying this table
        try:
            existing_cols = [
                c["name"] for c in inspector.get_columns(table_name)
            ]
        except Exception:
            # Table might not exist yet; let the batch operation handle it
            existing_cols = []

        if "layer_id" in existing_cols:
            # Column already present; skip to avoid re-creating tables
            continue

        # Add layer_id column with batch operation for SQLite compatibility
        with op.batch_alter_table(table_name, recreate="always") as batch_op:
            # Add the layer_id column (nullable for existing records)
            batch_op.add_column(
                sa.Column("layer_id", sa.Integer, nullable=True)
            )

            # Add foreign key constraint
            batch_op.create_foreign_key(
                f"fk_{table_name}_layer_id",
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
    ]
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for model in settings_models:
        table_name = model.__tablename__

        # If the table/column doesn't exist, skip
        try:
            existing_cols = [
                c["name"] for c in inspector.get_columns(table_name)
            ]
        except Exception:
            existing_cols = []

        if "layer_id" not in existing_cols:
            continue

        with op.batch_alter_table(table_name, recreate="always") as batch_op:
            # Drop foreign key constraint first (if present)
            try:
                batch_op.drop_constraint(
                    f"fk_{table_name}_layer_id", type_="foreignkey"
                )
            except Exception:
                # Constraint might not exist; ignore
                pass

            # Drop the layer_id column
            try:
                batch_op.drop_column("layer_id")
            except Exception:
                # Column might have been removed already; ignore
                pass
