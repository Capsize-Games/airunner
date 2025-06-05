"""add generate_infinite_images column

Revision ID: 72977a42e2a2
Revises: 738edc36e34f
Create Date: 2025-05-18 07:53:21.770502

"""

from typing import Sequence, Union

from airunner.components.art.data.generator_settings import GeneratorSettings
from airunner.utils.db import add_column, drop_column


# revision identifiers, used by Alembic.
revision: str = "72977a42e2a2"
down_revision: Union[str, None] = "738edc36e34f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column(GeneratorSettings, "generate_infinite_images")


def downgrade() -> None:
    drop_column(GeneratorSettings, "generate_infinite_images")
