"""Add tabs table

Revision ID: 5dbbe8800572
Revises: c0f6743e26e9
Create Date: 2025-03-12 02:50:18.985375

"""
from typing import Sequence, Union

from airunner.data.models import Tab
from airunner.utils.db import add_table, drop_table


# revision identifiers, used by Alembic.
revision: str = '5dbbe8800572'
down_revision: Union[str, None] = 'c0f6743e26e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_table(Tab)
    default_tabs = {
        "left": [
            {
                "name": "Chat",
                "index": 0,
                "active": True,
            },
        ],
        "center": [
            {
                "name": "Canvas",
                "index": 0,
                "active": True,
            },
            {
                "name": "Browser",
                "index": 1,
                "active": False,
            },
            {
                "name": "Document",
                "index": 2,
                "active": False,
            },
            {
                "name": "Game",
                "index": 3,
                "active": False,
            },
        ],
        "right": [
            {
                "name": "LLM",
                "index": 0,
                "active": True,
            },
            {
                "name": "Chat History",
                "index": 1,
                "active": False,
            },
        ],
    }
    for section in default_tabs.keys():
        for tab in default_tabs[section]:
            item = Tab.objects.filter_by(
                section=section,
                name=tab["name"],
            ).first()
            if not item:
                Tab.objects.create(
                    section=section,
                    name=tab["name"],
                    index=tab["index"],
                    active=tab["active"],
                )


def downgrade() -> None:
    drop_table(Tab)