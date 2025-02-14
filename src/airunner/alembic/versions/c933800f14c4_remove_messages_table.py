from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c933800f14c4'
down_revision: Union[str, None] = '6579bf48ed83'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table('messages')


def downgrade() -> None:
    op.create_table('messages',
    sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
    sa.Column('role', sa.String(), nullable=False),
    sa.Column('content', sa.String(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), default=sa.func.now()),
    sa.Column('conversation_id', sa.Integer(), sa.ForeignKey('conversations.id')),
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('is_bot', sa.Boolean(), default=False),
    sa.Column('chatbot_id', sa.Integer(), sa.ForeignKey('chatbots.id')),
    sa.ForeignKeyConstraint(['chatbot_id'], ['chatbots.id']),
    sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'])
    )