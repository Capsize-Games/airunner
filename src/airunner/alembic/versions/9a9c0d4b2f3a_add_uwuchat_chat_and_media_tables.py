"""Add UwUChat chat/media tables

Revision ID: 9a9c0d4b2f3a
Revises: 080398045849
Create Date: 2025-12-26

"""

from typing import Sequence, Union

from airunner.components.uwuchat.data.models.chat import (
    UwUChatMessage,
    UwUChatMedia,
    UwUChatProfile,
    UwUChatSession,
)
from airunner.utils.db.table import add_table, drop_table


# revision identifiers, used by Alembic.
revision: str = "9a9c0d4b2f3a"
down_revision: Union[str, None] = "080398045849"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_table(UwUChatSession)
    add_table(UwUChatMessage)
    add_table(UwUChatMedia)
    add_table(UwUChatProfile)


def downgrade() -> None:
    drop_table(UwUChatProfile)
    drop_table(UwUChatMedia)
    drop_table(UwUChatMessage)
    drop_table(UwUChatSession)
