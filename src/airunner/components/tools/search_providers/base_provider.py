"""Base search provider interface for search tools."""

from abc import ABC, abstractmethod
from typing import Any, List, Dict, Optional

import aiohttp

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


class BaseSearchProvider(ABC):
    """Abstract base class for search providers.

    All search providers implement async search methods and share
    common utilities for formatting results and HTTP client management.
    """

    def __init__(self):
        """Initialize the base search provider."""
        self._logger = None

    @staticmethod
    def _format_result(
        title: str,
        link: str,
        snippet: str = "",
        source: str = "",
        date: str = "",
    ) -> Dict[str, str]:
        """Format a search result into a standard dictionary.

        Args:
            title: Result title
            link: Result URL
            snippet: Result snippet/description
            source: Source name (for news results)
            date: Publication date (for news results)

        Returns:
            Formatted result dictionary
        """
        result = {
            "title": title.strip(),
            "link": link.strip(),
            "snippet": snippet.strip(),
        }
        if source:
            result["source"] = source.strip()
        if date:
            result["date"] = date.strip()
        return result

    @staticmethod
    async def get_async_client() -> aiohttp.ClientSession:
        """Create a new aiohttp ClientSession.

        Returns:
            Configured aiohttp ClientSession with 20s timeout
        """
        return aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20.0))

    @abstractmethod
    async def search(
        self,
        query: str,
        num_results: int = 10,
        client: Optional[aiohttp.ClientSession] = None,
    ) -> List[Dict[str, str]]:
        """Perform a search query.

        Args:
            query: Search query string
            num_results: Maximum number of results to return
            client: Optional existing aiohttp ClientSession

        Returns:
            List of formatted result dictionaries
        """

    @property
    def logger(self) -> Any:
        """Get logger for this provider."""
        if self._logger is None:
            self._logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
        return self._logger
