"""Add news tables

Revision ID: c2c5d4cd4b80
Revises: 3473f48885c9
Create Date: 2025-02-10 11:46:14.947103

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = 'c2c5d4cd4b80'
down_revision: Union[str, None] = '3473f48885c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)

    if 'news_rss_feeds' not in inspector.get_table_names():
        op.create_table(
            'news_rss_feeds',
            sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
            sa.Column('url', sa.String, nullable=False),
            sa.Column('name', sa.String, nullable=False),
            sa.Column('category', sa.String, nullable=False),
            sa.Column('political_bias', sa.String, nullable=True),
            sa.Column('last_scraped', sa.DateTime, nullable=True)
        )

    if 'news_categories' not in inspector.get_table_names():
        op.create_table(
            'news_categories',
            sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
            sa.Column('name', sa.String, nullable=False)
        )

    if 'news_articles' not in inspector.get_table_names():
        op.create_table(
            'news_articles',
            sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
            sa.Column('title', sa.String, nullable=False),
            sa.Column('source', sa.String, nullable=False),
            sa.Column('description', sa.String, nullable=True),
            sa.Column('image', sa.LargeBinary, nullable=True),
            sa.Column('content', sa.Text, nullable=True),
            sa.Column('status', sa.String, nullable=False, default='new'),
            sa.Column('scraped_at', sa.DateTime, default=sa.func.now())
        )

    if 'article_category_association' not in inspector.get_table_names():
        op.create_table(
            'article_category_association',
            sa.Column('article_id', sa.Integer, sa.ForeignKey('news_articles.id')),
            sa.Column('category_id', sa.Integer, sa.ForeignKey('news_categories.id'))
        )

    # Insert data into news_rss_feeds
    news_rss_feeds_table = sa.table(
        'news_rss_feeds',
        sa.column('url', sa.String),
        sa.column('name', sa.String),
        sa.column('category', sa.String),
        sa.column('political_bias', sa.String)
    )

    op.bulk_insert(news_rss_feeds_table, [
        # Left
        {'url': 'http://rss.cnn.com/rss/edition.rss', 'name': 'CNN', 'category': 'General', 'political_bias': 'Left'},
        {'url': 'https://www.theguardian.com/world/rss', 'name': 'The Guardian', 'category': 'General', 'political_bias': 'Left'},
        {'url': 'https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml', 'name': 'New York Times', 'category': 'General', 'political_bias': 'Left'},

        {'url': 'http://rss.cnn.com/rss/edition_world.rss', 'name': 'CNN World', 'category': 'World', 'political_bias': 'Left'},
        {'url': 'https://feeds.washingtonpost.com/rss/politics', 'name': 'Washington Post', 'category': 'US', 'political_bias': 'Left'},
        
        {'url': 'https://www.bloomberg.com/feed/podcast/bloomberg-businessweek.xml', 'name': 'Bloomberg Business', 'category': 'Business', 'political_bias': 'Left'},
        {'url': 'http://rss.cnn.com/rss/money_latest.rss', 'name': 'CNN Money', 'category': 'Business', 'political_bias': 'Left'},

        {'url': 'https://www.wired.com/feed/rss', 'name': 'Wired', 'category': 'Technology', 'political_bias': 'Left'},
        {'url': 'http://feeds.arstechnica.com/arstechnica/index', 'name': 'Ars Technica', 'category': 'Technology', 'political_bias': 'Left'},

        {'url': 'https://www.rollingstone.com/music/music-news/feed/', 'name': 'Rolling Stone', 'category': 'Entertainment', 'political_bias': 'Left'},
        {'url': 'https://kotaku.com/rss', 'name': 'Kotaku', 'category': 'Gaming', 'political_bias': 'Left'},
        {'url': 'https://www.scientificamerican.com/feed/', 'name': 'Scientific American', 'category': 'Science', 'political_bias': 'Left'},
        
        {'url': 'https://www.politico.com/rss/politics08.xml', 'name': 'Politico', 'category': 'Politics', 'political_bias': 'Left'},
        {'url': 'http://rss.cnn.com/rss/cnn_allpolitics.rss', 'name': 'CNN Politics', 'category': 'Politics', 'political_bias': 'Left'},

        # Right
        {'url': 'https://www.foxnews.com/about/rss', 'name': 'Fox News', 'category': 'General', 'political_bias': 'Right'},
        {'url': 'https://www.theepochtimes.com/feed', 'name': 'The Epoch Times', 'category': 'General', 'political_bias': 'Right'},
        {'url': 'https://www.washingtontimes.com/rss/headlines/news/', 'name': 'The Washington Times', 'category': 'General', 'political_bias': 'Right'},

        {'url': 'https://www.foxnews.com/us.xml', 'name': 'Fox News US', 'category': 'World', 'political_bias': 'Right'},
        {'url': 'https://www.washingtontimes.com/rss/headlines/national/', 'name': 'The Washington Times - National', 'category': 'US', 'political_bias': 'Right'},
        
        {'url': 'https://www.forbes.com/business/feed/', 'name': 'Forbes', 'category': 'Business', 'political_bias': 'Right'},
        {'url': 'https://www.foxbusiness.com/category/markets.xml', 'name': 'Fox Business - Markets', 'category': 'Business', 'political_bias': 'Right'},

        {'url': 'https://www.foxnews.com/category/tech.xml', 'name': 'Fox News Technology', 'category': 'Technology', 'political_bias': 'Right'},
        {'url': 'https://www.outkick.com/feed/', 'name': 'OutKick Sports', 'category': 'Sports', 'political_bias': 'Right'},

        {'url': 'https://www.dailywire.com/entertainment/feed', 'name': 'Daily Wire Entertainment', 'category': 'Entertainment', 'political_bias': 'Right'},
        {'url': 'https://www.washingtontimes.com/rss/headlines/politics/', 'name': 'The Washington Times - Politics', 'category': 'Politics', 'political_bias': 'Right'},
        {'url': 'https://www.nationalreview.com/feed/', 'name': 'National Review', 'category': 'Politics', 'political_bias': 'Right'},
        
        {'url': 'https://redstate.com/feed', 'name': 'RedState', 'category': 'Politics', 'political_bias': 'Right'},
        {'url': 'https://thefederalist.com/feed/', 'name': 'The Federalist', 'category': 'Politics', 'political_bias': 'Right'}
    ])