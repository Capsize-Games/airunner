"""added allow hf downloads column

Revision ID: ee56e41aa8cb
Revises: 978459f9d332
Create Date: 2025-04-23 19:08:55.290482

"""

from typing import Sequence, Union

from airunner.data.models import ApplicationSettings
from airunner.utils.db import add_column, drop_column


# revision identifiers, used by Alembic.
revision: str = "ee56e41aa8cb"
down_revision: Union[str, None] = "978459f9d332"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column(ApplicationSettings, "allow_huggingface_downloads")


def downgrade() -> None:
    drop_column(ApplicationSettings, "allow_huggingface_downloads")
