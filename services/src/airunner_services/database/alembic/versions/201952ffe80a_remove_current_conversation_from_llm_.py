"""remove current conversation from llm generator settings

Revision ID: 201952ffe80a
Revises: b96406b64944
Create Date: 2025-05-27 12:13:11.496860

"""

from typing import Sequence, Union

from alembic import op

from airunner_services.database.models.llm_generator_settings import (
    LLMGeneratorSettings,
)
from airunner_services.database.db import (
    add_column_with_fk,
    drop_column_with_fk,
)

import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "201952ffe80a"
down_revision: Union[str, None] = "b96406b64944"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    _reject_unmappable_current_conversation_values()
    add_column_with_fk(
        LLMGeneratorSettings,
        "current_chatbot",
        sa.Integer,
        "chatbots",
        "id",
        "current_chatbot_fkey",
    )
    # Only drop the column and its FK, do not attempt to drop constraints separately
    drop_column_with_fk(
        LLMGeneratorSettings,
        "current_conversation",
        "current_conversation_fkey",
    )


def _reject_unmappable_current_conversation_values() -> None:
    """Prevent dropping persisted conversation IDs without a mapping."""
    bind = op.get_bind()
    columns = {
        column["name"]
        for column in sa.inspect(bind).get_columns(
            LLMGeneratorSettings.__tablename__
        )
    }
    if "current_conversation" not in columns:
        return

    value_exists = bind.execute(
        sa.text(
            "SELECT 1 FROM llm_generator_settings "
            "WHERE current_conversation IS NOT NULL LIMIT 1"
        )
    ).first()
    if value_exists:
        raise RuntimeError(
            "Cannot upgrade this revision safely: llm_generator_settings "
            "contains current_conversation values that would be discarded, "
            "and no lossless mapping to current_chatbot is defined. Preserve "
            "or resolve those values before retrying the migration."
        )


def downgrade() -> None:
    """Reject a rollback that cannot restore the removed conversation state."""
    raise RuntimeError(
        "Cannot downgrade this revision safely: current_conversation values "
        "were dropped during upgrade, and current_chatbot does not preserve "
        "them. Restore a pre-upgrade database backup; otherwise keep this "
        "revision and upgrade forward."
    )
