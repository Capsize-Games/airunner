"""add_mode_based_routing_settings

Revision ID: 4cd9977eb573
Revises: def3ae90b66d
Create Date: 2025-11-03 05:07:46.889231

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from airunner.utils.db import add_column, drop_column
from airunner.components.llm.data.llm_generator_settings import (
    LLMGeneratorSettings,
)


# revision identifiers, used by Alembic.
revision: str = "4cd9977eb573"
down_revision: Union[str, None] = "def3ae90b66d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add mode-based routing settings columns
    add_column(LLMGeneratorSettings, "use_mode_routing")
    add_column(LLMGeneratorSettings, "mode_override")
    add_column(LLMGeneratorSettings, "enable_trajectory_logging")


def downgrade() -> None:
    # Remove mode-based routing columns
    drop_column(LLMGeneratorSettings, "enable_trajectory_logging")
    drop_column(LLMGeneratorSettings, "mode_override")
    drop_column(LLMGeneratorSettings, "use_mode_routing")
