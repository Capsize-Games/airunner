"""add nodegraph settings

Revision ID: 904f01f8f439
Revises: 1a9e7c2de7c9
Create Date: 2025-05-17 06:08:53.850366

"""

from typing import Sequence, Union

from airunner.components.settings.data.application_settings import ApplicationSettings
from airunner.utils.db import add_column, drop_column

# revision identifiers, used by Alembic.
revision: str = "904f01f8f439"
down_revision: Union[str, None] = "1a9e7c2de7c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column(ApplicationSettings, "nodegraph_zoom")
    add_column(ApplicationSettings, "nodegraph_center_x")
    add_column(ApplicationSettings, "nodegraph_center_y")


def downgrade() -> None:
    drop_column(ApplicationSettings, "nodegraph_zoom")
    drop_column(ApplicationSettings, "nodegraph_center_x")
    drop_column(ApplicationSettings, "nodegraph_center_y")
