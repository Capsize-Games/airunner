# alembic/versions/c4fb749c3e22_add_chatbot_id_to_messages.py

"""Add chatbot_id to messages

Revision ID: c4fb749c3e22
Revises: 8ff7299a6708
Create Date: 2024-10-02 10:17:18.504117

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4fb749c3e22'
down_revision: Union[str, None] = '8ff7299a6708'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    with op.batch_alter_table('messages') as batch_op:
        # Add the chatbot_id column to the messages table
        batch_op.add_column(sa.Column('chatbot_id', sa.Integer(), nullable=True))

        # Create a foreign key constraint for chatbot_id
        batch_op.create_foreign_key(
            'fk_messages_chatbot_id',
            'chatbots',
            ['chatbot_id'],
            ['id']
        )


def downgrade():
    with op.batch_alter_table('messages') as batch_op:
        # Drop the foreign key constraint
        batch_op.drop_constraint('fk_messages_chatbot_id', type_='foreignkey')

        # Drop the chatbot_id column from the messages table
        batch_op.drop_column('chatbot_id')
