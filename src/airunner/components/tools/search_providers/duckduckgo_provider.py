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
from airunner.components.tools.web_content_extractor import WebContentExtractor


class DuckDuckGoProvider(BaseSearchProvider):
    """DuckDuckGo web search provider."""

    @staticmethod
    def _build_exclusion_query(query: str) -> str:
        """Add -site: exclusions to query for blocked domains.

        Args:
            query: Original search query

        Returns:
            Query with -site: exclusions appended
        """
        try:
            blocklist = WebContentExtractor.get_blocklist()

            # Limit to priority blocked domains to avoid query length issues
            # DDG has query length limits, so we can't exclude hundreds of sites
            priority_blocks = []
            for domain in blocklist:
                # Prioritize common low-quality or blocked domains
                if any(
                    bad in domain.lower()
                    for bad in [
                        "wikipedia",
                        "reuters",
                        "tandfonline",
                        "washingtonpost",
                        "compliancewire",
                        "nytimes",
                    ]
                ):
                    priority_blocks.append(domain)

            # Limit to 10 exclusions max to keep query reasonable
            priority_blocks = priority_blocks[:10]

            if priority_blocks:
                exclusions = " ".join(
                    [f"-site:{domain}" for domain in priority_blocks]
                )
                return f"{query} {exclusions}"
        except Exception:
            # If blocklist fails, just return original query
            pass

        return query

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
        # Add blocklist exclusions to query
        enhanced_query = self._build_exclusion_query(query)

        self.logger.info(f"Starting DuckDuckGo search for: {enhanced_query}")
        results = []
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(
                    enhanced_query,  # Use enhanced query with exclusions
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
        # Add blocklist exclusions to query
        enhanced_query = self._build_exclusion_query(query)

        self.logger.info(
            f"Starting DuckDuckGo NEWS search for: {enhanced_query}"
        )
        results = []
        try:
            with DDGS() as ddgs:
                for r in ddgs.news(
                    enhanced_query,  # Use enhanced query with exclusions
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
