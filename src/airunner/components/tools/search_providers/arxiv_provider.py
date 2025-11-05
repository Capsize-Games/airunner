"""arXiv search provider."""

import urllib.parse
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional

import aiohttp

from airunner.components.tools.search_providers.base_provider import (
    BaseSearchProvider,
)


class ArxivProvider(BaseSearchProvider):
    """arXiv academic search provider."""

    API_BASE_URL: str = "http://export.arxiv.org/api/query"

    async def search(
        self,
        query: str,
        num_results: int = 10,
        client: Optional[aiohttp.ClientSession] = None,
    ) -> List[Dict[str, str]]:
        """Perform arXiv academic search.

        Args:
            query: Search query string
            num_results: Maximum number of results
            client: Optional aiohttp client

        Returns:
            List of search results
        """
        self.logger.info(f"Starting arXiv search for: {query}")
        results = []
        formatted_query = urllib.parse.quote_plus(query)
        url = f"{self.API_BASE_URL}?search_query=all:{formatted_query}&start=0&max_results={num_results}"

        async_client = client or await self.get_async_client()
        try:
            async with async_client.get(url) as response:
                response.raise_for_status()
                content = await response.text()
                root = ET.fromstring(content)
                atom_ns = {"atom": "http://www.w3.org/2005/Atom"}

                for entry in root.findall("atom:entry", atom_ns):
                    title_e = entry.find("atom:title", atom_ns)
                    link_e = entry.find(
                        "atom:link[@rel='alternate']", atom_ns
                    ) or entry.find(
                        "atom:link[@type='application/pdf']", atom_ns
                    )
                    summary_e = entry.find("atom:summary", atom_ns)

                    title = (
                        title_e.text.strip()
                        if title_e is not None and title_e.text
                        else "N/A"
                    )
                    link = (
                        link_e.get("href", "#") if link_e is not None else "#"
                    )
                    snippet = (
                        summary_e.text.strip().replace("\n", " ")
                        if summary_e is not None and summary_e.text
                        else ""
                    )

                    results.append(
                        self._format_result(
                            title=title, link=link, snippet=snippet
                        )
                    )
                    if len(results) >= num_results:
                        break

                self.logger.info(
                    f"arXiv search completed. Found {len(results)} results."
                )
        except aiohttp.ClientResponseError as e:
            self.logger.error(
                f"arXiv API HTTP error: {e.status} - {e.message}"
            )
        except ET.ParseError as e:
            self.logger.error(f"arXiv XML parsing error: {e}")
        except Exception as e:
            self.logger.error(f"arXiv search error: {e}")
        finally:
            if not client:
                await async_client.close()

        return results
