"""remove enabled col from rag_settings

Revision ID: 9d76c1e50d8f
Revises: eda1c0c1f709
Create Date: 2025-10-08 06:50:38.452991

"""

from typing import Sequence, Union

from airunner.components.llm.data.rag_settings import RAGSettings
from airunner.utils.db.column import drop_column


# revision identifiers, used by Alembic.
revision: str = "9d76c1e50d8f"
down_revision: Union[str, None] = "eda1c0c1f709"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    drop_column(RAGSettings, "enabled")


def downgrade() -> None:
    pass
