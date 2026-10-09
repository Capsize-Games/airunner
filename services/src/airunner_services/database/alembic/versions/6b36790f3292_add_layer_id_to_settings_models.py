"""add_layer_id_to_settings_models

Revision ID: 6b36790f3292
Revises: b5f6cf56def4
Create Date: 2025-09-24 12:59:37.090166

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# Table names are inlined (not imported from models) so this historical
# revision stays importable after model removals. See issue #2249.
LAYER_SETTINGS_TABLES = (
    "drawing_pad_settings",
    "controlnet_settings",
    "image_to_image_settings",
    "outpaint_settings",
)


# revision identifiers, used by Alembic.
revision: str = "6b36790f3292"
down_revision: Union[str, None] = "b5f6cf56def4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add layer_id foreign key columns to settings models."""
    # Get inspector to check existing schema so this migration is idempotent
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_tables = set(inspector.get_table_names())
    for table_name in LAYER_SETTINGS_TABLES:
        if table_name not in existing_tables:
            # Retired tables are absent on fresh databases; nothing to do.
            continue
        # If the column already exists, skip modifying this table
        existing_cols = [c["name"] for c in inspector.get_columns(table_name)]

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
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table_name in LAYER_SETTINGS_TABLES:
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
