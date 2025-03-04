"""Update column in ShortcutKeys model

Revision ID: 3f2896b85ff3
Revises: f31260eb8751
Create Date: 2025-03-03 15:00:19.780194

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '3f2896b85ff3'
down_revision: Union[str, None] = 'f31260eb8751'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'sqlite':
        op.add_column('shortcut_keys', sa.Column('signal_new', sa.String(), nullable=False, server_default=''))
        op.execute('UPDATE shortcut_keys SET signal_new = signal')
        op.drop_column('shortcut_keys', 'signal')
        op.add_column('shortcut_keys', sa.Column('signal', sa.String(), nullable=False, server_default=''))
        op.execute('UPDATE shortcut_keys SET signal = signal_new')
        op.drop_column('shortcut_keys', 'signal_new')
    else:
        op.alter_column('shortcut_keys', 'signal',
                    existing_type=sa.Integer(),
                    type_=sa.String(),
                    nullable=False)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'sqlite':
        op.add_column('signal_new', sa.Column('signal_new', sa.String(), nullable=False))
        op.execute('UPDATE shortcut_keys SET signal_new = signal')
        op.drop_column('shortcut_keys', 'signal')
        op.add_column('shortcut_keys', sa.Column('signal', sa.String(), nullable=False))
        op.execute('UPDATE shortcut_keys SET signal = signal_new')
        op.drop_column('shortcut_keys', 'signal_new')
    else:
        op.alter_column('shortcut_keys', 'signal',
                    existing_type=sa.String(),
                    type_=sa.Integer(),
                    nullable=False)