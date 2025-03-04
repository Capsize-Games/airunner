"""adds last_updated_message_id to conversation table

Revision ID: f3d84a9d5049
Revises: 2c12bfc33385
Create Date: 2025-02-18 07:58:10.145832

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = 'f3d84a9d5049'
down_revision: Union[str, None] = '2c12bfc33385'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    columns_conversations = [col['name'] for col in inspector.get_columns('conversations')]

    try:
        if 'last_updated_message_id' not in columns_conversations:
            op.add_column('conversations', sa.Column('last_updated_message_id', sa.Integer(), nullable=True))
        else:
            print("Column 'last_updated_message_id' already exists, skipping add.")
    except sa.exc.OperationalError as e:
        print("Error adding column 'last_updated_message_id': ", e)


def downgrade() -> None:
    try:
        op.drop_column('conversations', 'last_updated_message_id')
    except Exception as e:
        print("Error dropping column 'last_updated_message_id': ", e)