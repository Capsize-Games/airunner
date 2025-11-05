"""DuckDuckGo search provider."""

from typing import List, Dict, Optional

import aiohttp
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
