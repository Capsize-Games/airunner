"""DuckDuckGo search provider."""

from typing import List, Dict, Optional

import aiohttp

try:
    # Try new package name first
    from ddgs import DDGS
except ImportError:
    # Fall back to old package name for compatibility
    from duckduckgo_search import DDGS

from airunner.components.tools.search_providers.base_provider import (
    BaseSearchProvider,
)


class DuckDuckGoProvider(BaseSearchProvider):
    """DuckDuckGo web search provider."""

    async def search(
        self,
        query: str,
        num_results: int = 10,
        client: Optional[aiohttp.ClientSession] = None,
    ) -> List[Dict[str, str]]:
        """Perform DuckDuckGo web search.

        Args:
            query: Search query string
            num_results: Maximum number of results
            client: Optional aiohttp client (unused, kept for interface consistency)

        Returns:
            List of search results
        """
        self.logger.info(f"Starting DuckDuckGo search for: {query}")
        results = []
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(
                    query,
                    region="wt-wt",
                    safesearch="Moderate",
                    max_results=num_results,
                ):
                    results.append(
                        self._format_result(
                            title=r.get("title", "N/A"),
                            link=r.get("href", r.get("url", "#")),
                            snippet=r.get("body", r.get("snippet", "")),
                        )
                    )
                    if len(results) >= num_results:
                        break
            self.logger.info(
                f"DuckDuckGo search completed. Found {len(results)} results."
            )
        except Exception as e:
            self.logger.error(f"DuckDuckGo search error: {e}")
        return results

    async def news_search(
        self,
        query: str,
        num_results: int = 10,
        client: Optional[aiohttp.ClientSession] = None,
    ) -> List[Dict[str, str]]:
        """Perform DuckDuckGo news search for current events.

        News search is better for:
        - Recent events and breaking news
        - Current political developments
        - Recent appointments, decisions, actions
        - Time-sensitive information

        Args:
            query: Search query string
            num_results: Maximum number of results
            client: Optional aiohttp client (unused, kept for interface consistency)

        Returns:
            List of news article results
        """
        self.logger.info(f"Starting DuckDuckGo NEWS search for: {query}")
        results = []
        try:
            with DDGS() as ddgs:
                for r in ddgs.news(
                    query,
                    region="wt-wt",
                    safesearch="Moderate",
                    max_results=num_results,
                ):
                    # News results have slightly different structure
                    results.append(
                        self._format_result(
                            title=r.get("title", "N/A"),
                            link=r.get("url", r.get("href", "#")),
                            snippet=r.get(
                                "body", r.get("excerpt", r.get("snippet", ""))
                            ),
                            source=r.get("source", ""),
                            date=r.get("date", ""),
                        )
                    )
                    if len(results) >= num_results:
                        break
            self.logger.info(
                f"DuckDuckGo news search completed. Found {len(results)} results."
            )
        except Exception as e:
            self.logger.error(f"DuckDuckGo news search error: {e}")
        return results
