"""Create KeyboardShortcut table

Revision ID: 2d50ba1fd8ca
Revises: 98be29ddea23
Create Date: 2024-10-01 20:10:31.589431

"""
from typing import Sequence, Union

import sqlalchemy
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

from airunner.settings import DEFAULT_SHORTCUTS

# revision identifiers, used by Alembic.
revision: str = '2d50ba1fd8ca'
down_revision: Union[str, None] = '98be29ddea23'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    try:
        op.create_table(
            'keyboard_shortcuts',
            sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
            sa.Column('display_name', sa.String, nullable=False),
            sa.Column('text', sa.String, nullable=False),
            sa.Column('key', sa.Integer, nullable=False),
            sa.Column('modifiers', sa.Integer, nullable=False),
            sa.Column('description', sa.String, nullable=False),
            sa.Column('signal', sa.Integer, nullable=False)
        )
    except sqlalchemy.exc.OperationalError:
        pass

    keyboard_shortcut_table = sa.table(
        'keyboard_shortcuts',
        sa.Column('display_name', sa.String, nullable=False),
        sa.Column('text', sa.String, nullable=False),
        sa.Column('key', sa.Integer, nullable=False),
        sa.Column('modifiers', sa.Integer, nullable=False),
        sa.Column('description', sa.String, nullable=False),
        sa.Column('signal', sa.Integer, nullable=False)
    )

    op.bulk_insert(
        keyboard_shortcut_table,
        [
            {
                'display_name': shortcut['display_name'],
                'text': shortcut['text'],
                'key': shortcut['key'],
                'modifiers': shortcut['modifiers'],
                'description': shortcut['description'],
                'signal': shortcut['signal']
            }
            for shortcut in DEFAULT_SHORTCUTS
        ]
    )

def downgrade():
    op.drop_table('keyboard_shortcuts')
    # ### end Alembic commands ###
