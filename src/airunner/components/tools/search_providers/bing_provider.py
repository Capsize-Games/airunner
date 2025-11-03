"""Bing search provider."""

import os
from typing import List, Dict, Optional

import aiohttp

from airunner.components.tools.search_providers.base_provider import (
    BaseSearchProvider,
)


class BingProvider(BaseSearchProvider):
    """Bing web search provider."""

    SUBSCRIPTION_KEY: Optional[str] = os.getenv("BING_SUBSCRIPTION_KEY")
    ENDPOINT_URL: str = os.getenv(
        "BING_ENDPOINT_URL", "https://api.bing.microsoft.com/v7.0/search"
    )

    async def search(
        self,
        query: str,
        num_results: int = 10,
        client: Optional[aiohttp.ClientSession] = None,
    ) -> List[Dict[str, str]]:
        """Perform Bing web search.

        Args:
            query: Search query string
            num_results: Maximum number of results
            client: Optional aiohttp client

        Returns:
            List of search results
        """
        self.logger.info(f"Starting Bing search for: {query}")
        if not self.SUBSCRIPTION_KEY:
            self.logger.warning(
                "Bing Subscription Key not configured. Skipping Bing search."
            )
            return []

        results = []
        headers = {"Ocp-Apim-Subscription-Key": self.SUBSCRIPTION_KEY}
        params = {
            "q": query,
            "count": num_results,
            "answerCount": num_results,
            "safeSearch": "Moderate",
        }

        async_client = client or await self.get_async_client()
        try:
            async with async_client.get(
                self.ENDPOINT_URL, headers=headers, params=params
            ) as response:
                response.raise_for_status()
                search_data = await response.json()
                web_pages = search_data.get("webPages", {}).get("value", [])
                for page in web_pages:
                    results.append(
                        self._format_result(
                            title=page.get("name", "N/A"),
                            link=page.get("url", "#"),
                            snippet=page.get("snippet", ""),
                        )
                    )
                    if len(results) >= num_results:
                        break
                self.logger.info(
                    f"Bing search completed. Found {len(results)} results."
                )
        except aiohttp.ClientResponseError as e:
            self.logger.error(f"Bing API HTTP error: {e.status} - {e.message}")
        except Exception as e:
            self.logger.error(f"Bing search error: {e}")
        finally:
            if not client:
                await async_client.close()

        return results
