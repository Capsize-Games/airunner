"""DuckDuckGo search provider."""

from typing import List, Dict, Optional

import aiohttp

try:
    # Try new package name first
    from ddgs import DDGS
except ImportError:
    # Fall back to old package name for compatibility
    from duckduckgo_search import DDGS

from airunner_services.tools.search_providers.base_provider import (
    BaseSearchProvider,
)
from airunner_services.tools.web_content_extractor import WebContentExtractor
from airunner_services.utils.application.log_hygiene import summarize_text


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
            num_results: Maximum number of results to return (after filtering)
            client: Optional aiohttp client (unused, kept for interface consistency)

        Returns:
            List of search results (filtered by blocklist)
        """
        # Don't add exclusions to query - DDG doesn't respect them properly
        # Instead, we'll filter results after fetching
        self.logger.info(
            "Starting DuckDuckGo search (%s)",
            summarize_text(query, label="query"),
        )

        # Fetch MORE results than requested to account for filtering
        fetch_count = (
            num_results * 5
        )  # Fetch 5x to ensure we have enough after filtering

        all_results = []
        try:
            blocklist = WebContentExtractor.get_blocklist()
            with DDGS() as ddgs:
                all_results = self._collect_search_results(
                    ddgs, query, fetch_count, blocklist, num_results
                )
            self.logger.info(
                f"DuckDuckGo search completed. Found {len(all_results)} results after filtering."
            )
        except Exception as e:
            self.logger.error(f"DuckDuckGo search error: {e}")
        return all_results

    def _collect_search_results(self, ddgs, query: str, fetch_count: int, blocklist, num_results: int) -> List[Dict[str, str]]:
        """Fetch and blocklist-filter one query's search results."""
        from urllib.parse import urlparse

        all_results = []
        for r in ddgs.text(
            query,
            region="wt-wt",
            safesearch="Moderate",
            max_results=fetch_count,
        ):
            link = r.get("href", r.get("url", "#"))
            try:
                domain = urlparse(link).netloc.lower()
                if domain.startswith("www."):
                    domain = domain[4:]
                is_blocked = any(
                    domain == blocked or domain.endswith("." + blocked)
                    for blocked in blocklist
                )
                if is_blocked:
                    self.logger.debug(f"Filtered blocked domain: {domain}")
                    continue
            except Exception:
                pass
            all_results.append(
                self._format_result(
                    title=r.get("title", "N/A"),
                    link=link,
                    snippet=r.get("body", r.get("snippet", "")),
                )
            )
            if len(all_results) >= num_results:
                break
        return all_results

    def _collect_news_results(self, ddgs, query: str, fetch_count: int, blocklist, num_results: int) -> List[Dict[str, str]]:
        """Fetch and blocklist-filter one query's news results."""
        from urllib.parse import urlparse

        all_results = []
        for r in ddgs.news(
            query,
            region="wt-wt",
            safesearch="Moderate",
            max_results=fetch_count,
        ):
            link = r.get("url", r.get("href", "#"))
            try:
                domain = urlparse(link).netloc.lower()
                if domain.startswith("www."):
                    domain = domain[4:]
                is_blocked = any(
                    domain == blocked or domain.endswith("." + blocked)
                    for blocked in blocklist
                )
                if is_blocked:
                    self.logger.debug(f"Filtered blocked domain: {domain}")
                    continue
            except Exception:
                pass
            all_results.append(
                self._format_result(
                    title=r.get("title", "N/A"),
                    link=link,
                    snippet=r.get(
                        "body", r.get("excerpt", r.get("snippet", ""))
                    ),
                    source=r.get("source", ""),
                    date=r.get("date", ""),
                )
            )
            if len(all_results) >= num_results:
                break
        return all_results

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
            num_results: Maximum number of results to return (after filtering)
            client: Optional aiohttp client (unused, kept for interface consistency)

        Returns:
            List of news article results (filtered by blocklist)
        """
        self.logger.info(
            "Starting DuckDuckGo news search (%s)",
            summarize_text(query, label="query"),
        )

        # Fetch MORE results than requested to account for filtering
        fetch_count = num_results * 5

        all_results = []
        try:
            blocklist = WebContentExtractor.get_blocklist()
            with DDGS() as ddgs:
                all_results = self._collect_news_results(
                    ddgs, query, fetch_count, blocklist, num_results
                )
            self.logger.info(
                f"DuckDuckGo news search completed. Found {len(all_results)} results after filtering."
            )
        except Exception as e:
            self.logger.error(f"DuckDuckGo news search error: {e}")
        return all_results
