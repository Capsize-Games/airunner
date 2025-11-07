"""
zimreader.py

Provides ZIMReader for querying ZIM archives using libzim.

"""

from typing import Optional, List
from libzim.reader import Archive, Entry
from libzim.search import Query, Searcher

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class ZIMReader:
    """ZIMReader provides search and retrieval for ZIM archives using libzim.

    Args:
        zim_file_path (str): Path to the ZIM archive file.
    """

    def __init__(self, zim_file_path: str) -> None:
        self.zim_file_path = zim_file_path
        try:
            self.archive = Archive(zim_file_path)
            # Log available methods for debugging
            logger.debug(
                f"Archive methods: {[m for m in dir(self.archive) if not m.startswith('_')]}"
            )
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
            content_bytes = entry.get_item().content
            return content_bytes.tobytes().decode("utf-8")
        except Exception as e:
            logger.warning(f"Article not found or failed to read: {path}: {e}")
            return None

    def get_all_entry_paths(self, limit: Optional[int] = None) -> List[str]:
        """Get entry paths from the ZIM archive by random sampling.

        Since libzim's Python bindings don't support iteration, we use
        get_random_entry() to sample entries from the archive.

        Args:
            limit (Optional[int]): Maximum number of entries to return. Default 1000.

        Returns:
            List[str]: List of canonical paths for entries.
        """
        paths = []
        seen_paths = set()

        try:
            # Get entry count to know archive size
            entry_count = self.archive.entry_count
            logger.info(f"Archive has {entry_count} total entries")

            # Set reasonable limit
            max_entries = limit if limit else min(1000, entry_count)

            # Use get_random_entry() to sample entries
            # Sample more than needed since we'll filter some out
            attempts = (
                max_entries * 3
            )  # Try 3x to account for redirects/metadata

            for _ in range(attempts):
                if len(paths) >= max_entries:
                    break

                try:
                    entry = self.archive.get_random_entry()

                    # Skip redirects and metadata
                    if entry.is_redirect:
                        continue

                    path = entry.path

                    # Filter metadata entries and avoid duplicates
                    if not path.startswith("-/") and path not in seen_paths:
                        paths.append(path)
                        seen_paths.add(path)

                except Exception as e:
                    logger.debug(f"Error getting random entry: {e}")
                    continue

            logger.info(
                f"Successfully retrieved {len(paths)} unique entry paths"
            )

        except Exception as e:
            logger.error(f"Failed to enumerate entries: {e}")

        return paths

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
            # Modern libzim API: Query constructor takes the query string directly
            q = Query(query) if query else Query("")
            search = searcher.search(q)
            return [result.path for result in search.getResults(0, limit)]
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            return []
