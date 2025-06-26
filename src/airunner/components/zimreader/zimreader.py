"""
zimreader.py

Provides ZIMReader for querying ZIM archives using libzim.

"""

from typing import Optional, List
import logging
from libzim.reader import Archive, Entry
from libzim.search import Query, Searcher

logger = logging.getLogger(__name__)


class ZIMReader:
    """ZIMReader provides search and retrieval for ZIM archives using libzim.

    Args:
        zim_file_path (str): Path to the ZIM archive file.
    """

    def __init__(self, zim_file_path: str) -> None:
        self.zim_file_path = zim_file_path
        try:
            self.archive = Archive(zim_file_path)
        except Exception as e:
            logger.error(f"Failed to open ZIM archive: {zim_file_path}: {e}")
            raise

    def get_article(self, path: str) -> Optional[str]:
        """Retrieve article HTML content by canonical path.

        Args:
            path (str): Canonical ZIM path (e.g., 'A/Albert_Einstein.html').

        Returns:
            Optional[str]: HTML content if found, else None.
        """
        try:
            entry: Entry = self.archive.get_entry_by_path(path)
            content_bytes = entry.get_item().read()
            return content_bytes.decode("utf-8")
        except Exception as e:
            logger.warning(f"Article not found or failed to read: {path}: {e}")
            return None

    def search(self, query: str, limit: int = 5) -> List[str]:
        """Full-text search for articles in the ZIM archive.

        Args:
            query (str): Search query string.
            limit (int): Maximum number of results.

        Returns:
            List[str]: List of canonical paths for matching articles.
        """
        try:
            searcher = Searcher(self.archive)
            q = Query().with_query(query)
            search = searcher.search(q)
            return [result.path for result in search.get_results(0, limit)]
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            return []
