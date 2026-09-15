"""move api keys to os keyring

Revision ID: a7c93f2e1b4d
Revises: f0b1f4cf8f41
Create Date: 2026-08-17 06:30:00.000000

GitHub issue #2035: existing plaintext API keys (HuggingFace read/write,
CivitAI, LLM provider) are moved into the OS keyring (when available) and
the database columns are cleared. When no keyring backend is available the
columns are left untouched so the documented plaintext fallback keeps
working in headless/unattended environments.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from airunner_services.database.secret_store import (
    keyring_available,
    store_secret,
)

# revision identifiers, used by Alembic.
revision: str = "a7c93f2e1b4d"
down_revision: Union[str, None] = "f0b1f4cf8f41"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = {
    "application_settings": (
        "hf_api_key_read_key",
        "hf_api_key_write_key",
        "civit_ai_api_key",
    ),
    "llm_generator_settings": ("api_key",),
}


def upgrade() -> None:
    if not keyring_available():
        # No keyring backend; keep the plaintext fallback in place.
        return
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    for table_name, columns in _TABLES.items():
        if table_name not in existing_tables:
            continue
        table_columns = {
            column["name"] for column in inspector.get_columns(table_name)
        }
        for column_name in columns:
            if column_name not in table_columns:
                continue
            rows = bind.execute(
                sa.text(
                    f"SELECT id, {column_name} FROM {table_name} "
                    f"WHERE {column_name} IS NOT NULL "
                    f"AND {column_name} != ''"
                )
            ).fetchall()
            for row_id, value in rows:
                if not value:
                    continue
                store_secret(column_name, str(value))
                bind.execute(
                    sa.text(
                        f"UPDATE {table_name} SET {column_name}=:empty "
                        f"WHERE id=:id"
                    ),
                    {"empty": "", "id": row_id},
                )


def downgrade() -> None:
    # Keyring entries cannot be reliably restored into the database; the
    # columns are intentionally left empty. Keyring entries remain readable.
    pass
