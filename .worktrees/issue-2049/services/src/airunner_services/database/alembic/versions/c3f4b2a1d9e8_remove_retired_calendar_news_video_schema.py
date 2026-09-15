"""remove retired calendar, news, and video schema

Revision ID: c3f4b2a1d9e8
Revises: 970363fddcd6
Create Date: 2026-04-30 00:00:01.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c3f4b2a1d9e8"
down_revision: Union[str, None] = "970363fddcd6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _drop_table_if_present(table_name: str) -> None:
    if _has_table(table_name):
        op.drop_table(table_name)


def upgrade() -> None:
    for table_name in (
        "article_category_association",
        "calendar_reminders",
        "calendar_events",
        "recurring_events",
        "news_articles",
        "news_categories",
        "news_rss_feeds",
        "video_projects",
    ):
        _drop_table_if_present(table_name)


def downgrade() -> None:
    """Retired features are not restored on downgrade."""
    return None