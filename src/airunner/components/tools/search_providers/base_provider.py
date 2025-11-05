"""Base search provider interface for search tools."""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional

import aiohttp


class BaseSearchProvider(ABC):
    """Abstract base class for search providers.

    All search providers implement async search methods and share
    common utilities for formatting results and HTTP client management.
    """

    @staticmethod
    def _format_result(
        title: str, link: str, snippet: str = ""
    ) -> Dict[str, str]:
        """Format a search result into a standard dictionary.

        Args:
            title: Result title
            link: Result URL
            snippet: Result snippet/description

        Returns:
            Formatted result dictionary
        """
        return {
            "title": title.strip(),
            "link": link.strip(),
            "snippet": snippet.strip(),
        }

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
    def logger(self) -> logging.Logger:
        """Get logger for this provider."""
        return logging.getLogger(self.__class__.__name__)
