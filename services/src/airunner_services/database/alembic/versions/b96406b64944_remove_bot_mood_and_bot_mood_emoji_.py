"""Remove bot_mood and bot_mood_emoji columns from chatbot and conversation models

Revision ID: b96406b64944
Revises: 32782f73752d
Create Date: 2025-05-27 08:05:17.434637

"""

from typing import Sequence, Union

from airunner_services.database.models.conversation import Conversation
from airunner_services.database.db import drop_column


# revision identifiers, used by Alembic.
revision: str = "b96406b64944"
down_revision: Union[str, None] = "32782f73752d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    drop_column(Conversation, "bot_mood")


def downgrade() -> None:
    """Reject recovery that would silently discard or fabricate data."""
    raise RuntimeError(
        "Cannot downgrade: conversations.bot_mood and its per-row values "
        "were dropped. Restore a pre-upgrade database backup to recover the "
        "lost data; otherwise keep this revision and upgrade forward."
    )
