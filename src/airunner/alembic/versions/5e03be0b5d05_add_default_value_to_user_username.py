"""Add default value to User.username

Revision ID: 5e03be0b5d05
Revises: 4157bb294b34
Create Date: 2025-03-04 10:16:06.409255

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5e03be0b5d05'
down_revision: Union[str, None] = '4157bb294b34'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if op.get_bind().dialect.name == 'sqlite':
        op.execute("ALTER TABLE users RENAME COLUMN username TO username_old")
        op.execute("""
            ALTER TABLE users ADD COLUMN username VARCHAR(50) DEFAULT 'User'
        """)
        op.execute("""
            UPDATE users SET username = username_old WHERE username IS NULL
        """)
        op.execute("""
            ALTER TABLE users DROP COLUMN username_old
        """)
    else:
        op.alter_column('users', 'username', server_default='User')


def downgrade() -> None:
    if op.get_bind().dialect.name == 'sqlite':
        op.execute("ALTER TABLE users RENAME COLUMN username TO username_old")
        op.execute("""
            ALTER TABLE users ADD COLUMN username VARCHAR(50)
        """)
        op.execute("""
            UPDATE users SET username = username_old WHERE username IS NULL
        """)
        op.execute("""
            ALTER TABLE users DROP COLUMN username_old
        """)
    else:
        op.alter_column('users', 'username', server_default=None)