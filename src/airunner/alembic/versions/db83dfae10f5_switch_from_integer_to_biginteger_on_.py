"""Switch from Integer to BigInteger on seed columns

Revision ID: db83dfae10f5
Revises: 3f2896b85ff3
Create Date: 2025-03-03 15:12:13.927445

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.engine import Engine

# revision identifiers, used by Alembic.
revision: str = 'db83dfae10f5'
down_revision: Union[str, None] = '3f2896b85ff3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)

    if 'chatstore' not in inspector.get_table_names():
        op.create_table('chatstore',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('date_created', sa.String(), nullable=True),
            sa.Column('key', sa.String(), nullable=False),
            sa.Column('value', sa.JSON(), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )

    if 'chatbots' in inspector.get_table_names():
        if bind.dialect.name == 'sqlite':
            # SQLite does not support altering column types directly
            if 'chatbots_new' not in inspector.get_table_names():
                op.execute("CREATE TABLE chatbots_new AS SELECT * FROM chatbots;")
                op.execute("ALTER TABLE chatbots_new RENAME COLUMN seed TO seed_old;")
                op.execute("ALTER TABLE chatbots_new ADD COLUMN seed BIGINT;")
                op.execute("UPDATE chatbots_new SET seed = seed_old;")
                op.execute("ALTER TABLE chatbots_new DROP COLUMN seed_old;")
                op.execute("DROP TABLE chatbots;")
                op.execute("ALTER TABLE chatbots_new RENAME TO chatbots;")
        else:
            op.alter_column('chatbots', 'seed',
                existing_type=sa.Integer(),
                type_=sa.BigInteger(),
                existing_nullable=True
            )

    try:
        if 'conversations' in inspector.get_table_names() and 'users' in inspector.get_table_names():
            op.create_foreign_key(None, 'conversations', 'users', ['user_id'], ['id'])
    except Exception as e:
        print("Error creating foreign key: ", e)
    try:
        if 'conversations' in inspector.get_table_names() and 'chatbots' in inspector.get_table_names():
            op.create_foreign_key(None, 'conversations', 'chatbots', ['chatbot_id'], ['id'])
    except Exception as e:
        print("Error creating foreign key: ", e)

    if 'generator_settings' in inspector.get_table_names():
        if bind.dialect.name == 'sqlite':
            with op.batch_alter_table('generator_settings') as batch_op:
                batch_op.alter_column('seed', existing_type=sa.Integer(), type_=sa.BigInteger())
        else:
            op.alter_column('generator_settings', 'seed',
                existing_type=sa.Integer(),
                type_=sa.BigInteger(),
                existing_nullable=True
            )
        try:
            if 'generator_settings' in inspector.get_table_names() and 'aimodels' in inspector.get_table_names():
                op.create_foreign_key(None, 'generator_settings', 'aimodels', ['model'], ['id'])
        except Exception as e:
            print("Error creating foreign key: ", e)

    if 'llm_generator_settings' in inspector.get_table_names():
        if bind.dialect.name == 'sqlite':
            with op.batch_alter_table('llm_generator_settings') as batch_op:
                batch_op.alter_column('seed', existing_type=sa.Integer(), type_=sa.BigInteger())
        else:
            op.alter_column('llm_generator_settings', 'seed',
                existing_type=sa.Integer(),
                type_=sa.BigInteger(),
                existing_nullable=True
            )

    if 'news_articles' in inspector.get_table_names():
        if bind.dialect.name == 'sqlite':
            with op.batch_alter_table('news_articles') as batch_op:
                batch_op.create_unique_constraint('uq_news_articles_source', ['source'])
        else:
            op.create_unique_constraint('uq_news_articles_source', 'news_articles', ['source'])

    try:
        if 'summaries' in inspector.get_table_names() and 'conversations' in inspector.get_table_names():
            op.create_foreign_key(None, 'summaries', 'conversations', ['conversation_id'], ['id'])
    except Exception as e:
        print("Error creating foreign key: ", e)

    try:
        if 'target_directories' in inspector.get_table_names() and 'chatbots' in inspector.get_table_names():
            op.create_foreign_key(None, 'target_directories', 'chatbots', ['chatbot_id'], ['id'])
    except Exception as e:
        print("Error creating foreign key: ", e)

    try:
        if 'target_files' in inspector.get_table_names() and 'chatbots' in inspector.get_table_names():
            op.create_foreign_key(None, 'target_files', 'chatbots', ['chatbot_id'], ['id'])
    except Exception as e:
        print("Error creating foreign key: ", e)


def downgrade() -> None:
    bind = op.get_bind()
    op.drop_constraint(None, 'target_files', type_='foreignkey')
    op.drop_constraint(None, 'target_directories', type_='foreignkey')
    op.drop_constraint(None, 'summaries', type_='foreignkey')
    op.drop_constraint('uq_news_articles_source', 'news_articles', type_='unique')
    if bind.dialect.name == 'sqlite':
        with op.batch_alter_table('llm_generator_settings') as batch_op:
            batch_op.alter_column('seed', existing_type=sa.BigInteger(), type_=sa.Integer())
    else:
        op.alter_column('llm_generator_settings', 'seed',
            existing_type=sa.BigInteger(),
            type_=sa.Integer(),
            existing_nullable=True
        )
    op.drop_constraint(None, 'generator_settings', type_='foreignkey')
    if bind.dialect.name == 'sqlite':
        with op.batch_alter_table('generator_settings') as batch_op:
            batch_op.alter_column('seed', existing_type=sa.BigInteger(), type_=sa.Integer())
    else:
        op.alter_column('generator_settings', 'seed',
            existing_type=sa.BigInteger(),
            type_=sa.Integer(),
            existing_nullable=True
        )
    op.drop_constraint(None, 'conversations', type_='foreignkey')
    op.drop_constraint(None, 'conversations', type_='foreignkey')
    if bind.dialect.name == 'sqlite':
        with op.batch_alter_table('chatbots') as batch_op:
            batch_op.alter_column('seed', existing_type=sa.BigInteger(), type_=sa.Integer())
    else:
        op.alter_column('chatbots', 'seed',
            existing_type=sa.BigInteger(),
            type_=sa.Integer(),
            existing_nullable=True
        )
    op.drop_table('chatstore')