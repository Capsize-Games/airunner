from sqlalchemy import Column, Integer, String, Text, ForeignKey, LargeBinary, DateTime, Table
from sqlalchemy.orm import relationship

import datetime

from airunner.data.models.base import BaseModel, Base


article_category_association = Table(
    'article_category_association', Base.metadata,
    Column('article_id', Integer, ForeignKey('news_articles.id')),
    Column('category_id', Integer, ForeignKey('news_categories.id'))
)


class RSSFeed(BaseModel):
    __tablename__ = 'news_rss_feeds'
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String, nullable=False, default="")
    name = Column(String, nullable=False, default="")
    category = Column(String, nullable=False, default="")
    political_bias = Column(String, nullable=True)
    last_scraped = Column(DateTime, nullable=True)


class Category(BaseModel):
    __tablename__ = 'news_categories'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, default="")


class Article(BaseModel):
    __tablename__ = 'news_articles'
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False, default="")
    source = Column(String, nullable=False, unique=True, default="")
    description = Column(String, nullable=True)
    categories = relationship('Category', secondary=article_category_association, back_populates='articles')
    image = Column(LargeBinary, nullable=True)
    content = Column(Text, nullable=True)
    status = Column(String, nullable=False, default='new')
    scraped_at = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))


Category.articles = relationship('Article', secondary=article_category_association, back_populates='categories')
