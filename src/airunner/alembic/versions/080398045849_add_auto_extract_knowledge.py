"""Add auto_extract_knowledge to llm_generator_settings

Revision ID: 080398045849
Revises: 810df6adb9db
Create Date: 2025-01-26 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "080398045849"
down_revision = "810df6adb9db"
branch_labels = None
depends_on = None


def upgrade():
    """Add auto_extract_knowledge column to llm_generator_settings table."""
    # Check if column already exists
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    # Get existing columns
    columns = [
        col["name"] for col in inspector.get_columns("llm_generator_settings")
    ]

    if "auto_extract_knowledge" in columns:
        # Column already exists, skip
        return

    # Add column with default True for automatic knowledge extraction
    op.add_column(
        "llm_generator_settings",
        sa.Column(
            "auto_extract_knowledge",
            sa.Boolean(),
            nullable=True,
            server_default="1",
        ),
    )

    # Update existing rows to have the default value
    op.execute(
        "UPDATE llm_generator_settings SET auto_extract_knowledge = 1 WHERE auto_extract_knowledge IS NULL"
    )

    # Make column non-nullable after setting defaults
    with op.batch_alter_table("llm_generator_settings") as batch_op:
        batch_op.alter_column("auto_extract_knowledge", nullable=False)


def downgrade():
    """Remove auto_extract_knowledge column from llm_generator_settings table."""
    op.drop_column("llm_generator_settings", "auto_extract_knowledge")
