"""Change current_chatbot from string to integer

Revision ID: 8ff7299a6708
Revises: a19af7bc4d12
Create Date: 2024-10-02 09:56:32.103189

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '8ff7299a6708'
down_revision: Union[str, None] = 'a19af7bc4d12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    with op.batch_alter_table('llm_generator_settings') as batch_op:
        batch_op.alter_column('current_chatbot', type_=sa.Integer, postgresql_using='current_chatbot::integer')

def downgrade():
    # Revert the column type from Integer back to String
    with op.batch_alter_table('llm_generator_settings') as batch_op:
        batch_op.alter_column('current_chatbot', type_=sa.String)
    # ### end Alembic commands ###
