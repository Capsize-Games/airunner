"""
Browser component settings models.

This module defines the settings dataclass for the browser component, including support for private browsing, bookmarks (with folders), history, plaintext, and page summary.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class Bookmark(BaseModel):
    title: str
    url: str
    icon: Optional[str] = None  # base64 or url
    created_at: Optional[str] = None  # ISO8601
    updated_at: Optional[str] = None


class BookmarkFolder(BaseModel):
    name: str
    bookmarks: List[Bookmark] = Field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class HistoryEntry(BaseModel):
    title: str
    url: str
    visited_at: str  # ISO8601
    icon: Optional[str] = None


class BrowserSettings(BaseModel):
    name: str = "browser"
    private_browsing: bool = False
    random_user_agent: bool = False
    bookmarks: List[BookmarkFolder] = Field(default_factory=list)
    history: List[HistoryEntry] = Field(default_factory=list)
    plaintext: Optional[str] = None
    page_summary: Optional[str] = None

    class Config:
        title = "BrowserSettings"
        validate_assignment = True
