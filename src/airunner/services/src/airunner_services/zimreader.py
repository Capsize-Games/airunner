"""Service-owned ZIM archive reader helpers."""

from typing import List, Optional

from libzim.reader import Archive, Entry
from libzim.search import Query, Searcher

from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger
from airunner_services.utils.application.log_hygiene import summarize_text

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class ZIMReader:
    """Read and search content from one ZIM archive."""

    def __init__(self, zim_file_path: str) -> None:
        self.zim_file_path = zim_file_path
        try:
            self.archive = Archive(zim_file_path)
            methods = [
                method
                for method in dir(self.archive)
                if not method.startswith("_")
            ]
            logger.debug("Archive methods: %s", methods)
        except Exception as error:
            logger.error(
                "Failed to open ZIM archive %s: %s",
                zim_file_path,
                error,
            )
            raise

    def get_article(self, path: str) -> Optional[str]:
        """Return HTML content for one canonical ZIM path."""
        try:
            entry: Entry = self.archive.get_entry_by_path(path)
            content_bytes = entry.get_item().content
            return content_bytes.tobytes().decode("utf-8")
        except Exception as error:
            logger.warning(
                "Article lookup failed for %s: %s",
                path,
                error,
            )
            return None

    def get_all_entry_paths(self, limit: Optional[int] = None) -> List[str]:
        """Return sampled canonical entry paths from the archive."""
        paths: list[str] = []
        seen_paths: set[str] = set()

        try:
            entry_count = self.archive.entry_count
            logger.info("Archive has %s total entries", entry_count)

            max_entries = limit if limit else min(1000, entry_count)
            attempts = max_entries * 3

            for _ in range(attempts):
                if len(paths) >= max_entries:
                    break

                try:
                    entry = self.archive.get_random_entry()
                    if entry.is_redirect:
                        continue

                    path = entry.path
                    if path.startswith("-/") or path in seen_paths:
                        continue

                    paths.append(path)
                    seen_paths.add(path)
                except Exception as error:
                    logger.debug("Random entry lookup failed: %s", error)
                    continue

            logger.info(
                "Retrieved %s unique ZIM entry paths",
                len(paths),
            )
        except Exception as error:
            logger.error("Failed to enumerate ZIM entries: %s", error)

        return paths

    def search(self, query: str, limit: int = 5) -> List[str]:
        """Return canonical paths for one full-text ZIM search."""
        try:
            searcher = Searcher(self.archive)
            search = searcher.search(Query(query) if query else Query(""))
            return [result.path for result in search.getResults(0, limit)]
        except Exception as error:
            logger.error(
                "Search failed (%s): %s",
                summarize_text(query, label="query"),
                error,
            )
            return []