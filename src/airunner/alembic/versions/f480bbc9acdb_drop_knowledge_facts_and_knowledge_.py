"""drop knowledge_facts and knowledge_relationships tables

Revision ID: f480bbc9acdb
Revises: 9d70f20f2fed
Create Date: 2025-11-28 15:42:28.190695

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f480bbc9acdb'
down_revision: Union[str, None] = '9d70f20f2fed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the knowledge tables - we now use markdown-based knowledge base instead
    # Check if tables exist before dropping (SQLite compatibility)
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()
    
    if 'knowledge_relationships' in existing_tables:
        op.drop_table('knowledge_relationships')
    if 'knowledge_facts' in existing_tables:
        op.drop_table('knowledge_facts')
    if 'conversation_summaries' in existing_tables:
        op.drop_table('conversation_summaries')


def downgrade() -> None:
    # Recreate the tables if needed (not recommended)
    op.create_table(
        'knowledge_facts',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('category', sa.String(50), nullable=False, default='other'),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, default=0.9),
        sa.Column('source', sa.String(50), nullable=False, default='conversation'),
        sa.Column('source_conversation_id', sa.Integer(), nullable=True),
        sa.Column('verified', sa.Boolean(), nullable=False, default=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, default=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('last_accessed', sa.DateTime(), nullable=True),
        sa.Column('access_count', sa.Integer(), nullable=False, default=0),
    )
    op.create_table(
        'knowledge_relationships',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('source_fact_id', sa.Integer(), nullable=False),
        sa.Column('target_fact_id', sa.Integer(), nullable=True),
        sa.Column('relationship_type', sa.String(50), nullable=False),
        sa.Column('entity_name', sa.String(255), nullable=True),
        sa.Column('entity_type', sa.String(50), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, default=0.9),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )