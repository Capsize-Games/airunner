"""remove rate and volume from speech t5 settings

Revision ID: 1de875096dfc
Revises: f447116b8b54
Create Date: 2025-02-23 08:45:09.519557

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = '1de875096dfc'
down_revision: Union[str, None] = 'f447116b8b54'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    columns_speech_t5_settings = [col['name'] for col in inspector.get_columns('speech_t5_settings')]

    try:
        if 'rate' in columns_speech_t5_settings:
            op.drop_column('speech_t5_settings', 'rate')
        else:
            print("Column 'rate' does not exist, skipping drop.")
    except sa.exc.OperationalError as e:
        print("Error dropping column 'rate': ", e)

    try:
        if 'volume' in columns_speech_t5_settings:
            op.drop_column('speech_t5_settings', 'volume')
        else:
            print("Column 'volume' does not exist, skipping drop.")
    except sa.exc.OperationalError as e:
        print("Error dropping column 'volume': ", e)


def downgrade() -> None:
    op.add_column('speech_t5_settings', sa.Column('volume', sa.Float(), nullable=True))
    op.add_column('speech_t5_settings', sa.Column('rate', sa.Integer(), nullable=True))