"""
AggregatedSearchTool: Unified search interface for multiple web services.

Refactored to use provider pattern for better separation of concerns.
Each search provider is implemented as a separate class.

Example usage:
    results = AggregatedSearchTool.aggregated_search("python asyncio", category="web")
"""

import asyncio
from typing import List, Dict, Optional
from functools import lru_cache

from airunner.components.tools.search_providers import (
    DuckDuckGoProvider,
    BingProvider,
    ArxivProvider,
)
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class AggregatedSearchTool:
    """Static tool for performing aggregated searches across multiple services.

    Uses provider classes for each search service.
    Results are cached for efficiency.
    """

    # Service category mappings
    SERVICE_CATEGORIES = {
        "web": ["duckduckgo", "bing"],
        "academic": ["arxiv"],
        "news": [],  # Reserved for future implementation
        "code": [],  # Reserved for future implementation
        "books": [],  # Reserved for future implementation
        "q&a": [],  # Reserved for future implementation
    }

    # Provider instances (lazy-initialized)
    _providers = {
        "duckduckgo": None,
        "bing": None,
        "arxiv": None,
    }

    @classmethod
    def _get_provider(cls, provider_name: str):
        """Get or create a provider instance.

        Args:
            provider_name: Name of the provider

        Returns:
            Provider instance
        """
        if cls._providers[provider_name] is None:
            if provider_name == "duckduckgo":
                cls._providers[provider_name] = DuckDuckGoProvider()
            elif provider_name == "bing":
                cls._providers[provider_name] = BingProvider()
            elif provider_name == "arxiv":
                cls._providers[provider_name] = ArxivProvider()
        return cls._providers[provider_name]

    @staticmethod
    @lru_cache(maxsize=128)
    def _cache_key(query: str, category: str) -> str:
        """Generate cache key for query.

        Args:
            query: Search query
            category: Search category

        Returns:
            Cache key string
        """
        return f"{query.lower()}::{category.lower()}"

    @classmethod
    def _get_providers_for_category(cls, category: str) -> List[str]:
        """Get list of provider names for a category.

        Args:
            category: Search category or 'all'

        Returns:
            List of provider names
        """
        if category == "all":
            # Use all available providers
            return ["duckduckgo", "bing", "arxiv"]
        elif category in cls.SERVICE_CATEGORIES:
            return cls.SERVICE_CATEGORIES[category]
        else:
            logger.warning(f"Unknown category: {category}")
            return []

    @classmethod
    async def aggregated_search(
        cls, query: str, category: str = "all", num_results: int = 10
    ) -> Dict[str, List[Dict[str, str]]]:
        """Perform an aggregated search across multiple services.

        Args:
            query: The search query string
            category: Service category (web, academic, news, code, books, q&a, or 'all')
            num_results: Maximum results per provider

        Returns:
            Dict mapping service name to list of result dicts
        """
        results = {}

        # Determine which providers to use
        providers_to_use = cls._get_providers_for_category(category)

        # Execute searches for each provider
        for provider_name in providers_to_use:
            try:
                provider = cls._get_provider(provider_name)
                provider_results = await provider.search(query, num_results)
                results[provider_name] = provider_results
                logger.info(
                    f"{provider_name} search returned {len(provider_results)} results"
                )
            except Exception as e:
                logger.error(f"Error in {provider_name} search: {e}")
                results[provider_name] = []

        return results

    @classmethod
    def aggregated_search_sync(
        cls, query: str, category: str = "all", num_results: int = 10
    ) -> Dict[str, List[Dict[str, str]]]:
        """Synchronous wrapper for aggregated_search.

        For LLM tool compatibility.

        Args:
            query: The search query string
            category: Service category
            num_results: Maximum results per provider

        Returns:
            Dict mapping service name to list of result dicts
        """
        return asyncio.run(cls.aggregated_search(query, category, num_results))

    # Legacy static methods for backward compatibility (delegate to providers)
    @staticmethod
    async def search_bing(
        query: str, num_results: int = 10, client: Optional[object] = None
    ) -> List[Dict[str, str]]:
        """Legacy method - delegates to BingProvider."""
        provider = BingProvider()
        return await provider.search(query, num_results, client)

    @staticmethod
    async def search_arxiv(
        query: str, num_results: int = 10, client: Optional[object] = None
    ) -> List[Dict[str, str]]:
        """Legacy method - delegates to ArxivProvider."""
        provider = ArxivProvider()
        return await provider.search(query, num_results, client)

    @staticmethod
    async def search_duckduckgo(
        query: str, num_results: int = 10, client: Optional[object] = None
    ) -> List[Dict[str, str]]:
        """Legacy method - delegates to DuckDuckGoProvider."""
        provider = DuckDuckGoProvider()
        return await provider.search(query, num_results, client)
