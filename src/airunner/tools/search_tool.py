"""
AggregatedSearchTool: Unified search interface for multiple web services.

This tool provides a static, cache-enabled interface for performing aggregated searches across various online services (web, academic, news, code, books, Q&A).

All methods are static and results are cached for efficiency. Intended for use in NodeGraphQt nodes, LLM tool integrations, and other AI Runner components.

Example usage:
    results = AggregatedSearchTool.aggregated_search("python asyncio", category="web")

"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from functools import lru_cache

# Import all dependencies (assume they are installed as optional extras)
import aiohttp
from duckduckgo_search import DDGS
from googleapiclient.discovery import build as build_google_service
import wikipedia
import xml.etree.ElementTree as ET
import os
import urllib.parse
import json


class AggregatedSearchTool:
    """Static tool for performing aggregated searches across multiple services.

    All methods are static and results are cached for efficiency.
    """

    # --- Configuration (from environment variables) ---
    GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")
    GOOGLE_CSE_ID: Optional[str] = os.getenv("GOOGLE_CSE_ID")
    BING_SUBSCRIPTION_KEY: Optional[str] = os.getenv("BING_SUBSCRIPTION_KEY")
    BING_ENDPOINT_URL: str = os.getenv(
        "BING_ENDPOINT_URL", "https://api.bing.microsoft.com/v7.0/search"
    )
    ARXIV_API_BASE_URL: str = "http://export.arxiv.org/api/query"
    NEWSAPI_KEY: Optional[str] = os.getenv("NEWSAPI_KEY")
    NEWSAPI_ENDPOINT_URL: str = "https://newsapi.org/v2/everything"
    STACKEXCHANGE_KEY: Optional[str] = os.getenv("STACKEXCHANGE_KEY")
    STACKEXCHANGE_API_URL: str = "https://api.stackexchange.com/2.3/search/advanced"
    GITHUB_TOKEN: Optional[str] = os.getenv("GITHUB_TOKEN")
    GITHUB_API_SEARCH_REPOS_URL: str = "https://api.github.com/search/repositories"
    OPENLIBRARY_SEARCH_URL: str = "http://openlibrary.org/search.json"

    SERVICE_CATEGORIES = {
        "web": ["duckduckgo", "google", "bing"],
        "academic": ["wikipedia", "arxiv"],
        "news": ["newsapi"],
        "code": ["github_repos"],
        "books": ["openlibrary"],
        "q&a": ["stackexchange"],
    }

    @staticmethod
    def _format_result(title: str, link: str, snippet: str = "") -> Dict[str, str]:
        return {
            "title": title.strip(),
            "link": link.strip(),
            "snippet": snippet.strip(),
        }

    @staticmethod
    @lru_cache(maxsize=128)
    def _cache_key(query: str, category: str) -> str:
        return f"{query.lower()}::{category.lower()}"

    @staticmethod
    async def get_async_client() -> aiohttp.ClientSession:
        """Create a new aiohttp ClientSession."""
        return aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20.0))

    @staticmethod
    async def search_bing(
        query: str,
        num_results: int = 10,
        client: Optional[aiohttp.ClientSession] = None,
    ) -> List[Dict[str, str]]:
        logger = logging.getLogger(__name__)
        logger.info(f"Starting Bing search for: {query}")
        if not AggregatedSearchTool.BING_SUBSCRIPTION_KEY:
            logger.warning(
                "Bing Subscription Key not configured. Skipping Bing search."
            )
            return []
        results = []
        headers = {
            "Ocp-Apim-Subscription-Key": AggregatedSearchTool.BING_SUBSCRIPTION_KEY
        }
        params = {
            "q": query,
            "count": num_results,
            "answerCount": num_results,
            "safeSearch": "Moderate",
        }
        async_client = client or await AggregatedSearchTool.get_async_client()
        try:
            async with async_client.get(
                AggregatedSearchTool.BING_ENDPOINT_URL,
                headers=headers,
                params=params,
            ) as response:
                response.raise_for_status()
                search_data = await response.json()
                web_pages = search_data.get("webPages", {}).get("value", [])
                for page in web_pages:
                    results.append(
                        AggregatedSearchTool._format_result(
                            title=page.get("name", "N/A"),
                            link=page.get("url", "#"),
                            snippet=page.get("snippet", ""),
                        )
                    )
                    if len(results) >= num_results:
                        break
                logger.info(f"Bing search completed. Found {len(results)} results.")
        except aiohttp.ClientResponseError as e:
            logger.error(f"Bing API HTTP error: {e.status} - {e.message}")
        except Exception as e:
            logger.error(f"Bing search error: {e}")
        finally:
            if not client:
                await async_client.close()
        return results

    @staticmethod
    async def search_arxiv(
        query: str,
        num_results: int = 10,
        client: Optional[aiohttp.ClientSession] = None,
    ) -> List[Dict[str, str]]:
        logger = logging.getLogger(__name__)
        logger.info(f"Starting arXiv search for: {query}")
        results = []
        formatted_query = urllib.parse.quote_plus(query)
        url = f"{AggregatedSearchTool.ARXIV_API_BASE_URL}?search_query=all:{formatted_query}&start=0&max_results={num_results}"
        async_client = client or await AggregatedSearchTool.get_async_client()
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
                    ) or entry.find("atom:link[@type='application/pdf']", atom_ns)
                    summary_e = entry.find("atom:summary", atom_ns)
                    title = (
                        title_e.text.strip()
                        if title_e is not None and title_e.text
                        else "N/A"
                    )
                    link = link_e.get("href", "#") if link_e is not None else "#"
                    snippet = (
                        summary_e.text.strip().replace("\n", " ")
                        if summary_e is not None and summary_e.text
                        else ""
                    )
                    results.append(
                        AggregatedSearchTool._format_result(
                            title=title, link=link, snippet=snippet
                        )
                    )
                    if len(results) >= num_results:
                        break
                logger.info(f"arXiv search completed. Found {len(results)} results.")
        except aiohttp.ClientResponseError as e:
            logger.error(f"arXiv API HTTP error: {e.status} - {e.message}")
        except ET.ParseError as e:
            logger.error(f"arXiv XML parsing error: {e}")
        except Exception as e:
            logger.error(f"arXiv search error: {e}")
        finally:
            if not client:
                await async_client.close()
        return results

    @staticmethod
    async def search_newsapi(
        query: str,
        num_results: int = 10,
        client: Optional[aiohttp.ClientSession] = None,
    ) -> List[Dict[str, str]]:
        logger = logging.getLogger(__name__)
        logger.info(f"Starting NewsAPI.org search for: {query}")
        if not AggregatedSearchTool.NEWSAPI_KEY:
            logger.warning("NewsAPI Key not configured. Skipping NewsAPI search.")
            return []
        results = []
        params = {
            "q": query,
            "apiKey": AggregatedSearchTool.NEWSAPI_KEY,
            "pageSize": num_results,
            "language": "en",
        }
        async_client = client or await AggregatedSearchTool.get_async_client()
        try:
            async with async_client.get(
                AggregatedSearchTool.NEWSAPI_ENDPOINT_URL, params=params
            ) as response:
                response.raise_for_status()
                news_data = await response.json()
                articles = news_data.get("articles", [])
                for article in articles:
                    results.append(
                        AggregatedSearchTool._format_result(
                            title=article.get("title", "N/A"),
                            link=article.get("url", "#"),
                            snippet=article.get("description")
                            or article.get("content", "")
                            or "",
                        )
                    )
                    if len(results) >= num_results:
                        break
                logger.info(f"NewsAPI search completed. Found {len(results)} results.")
        except aiohttp.ClientResponseError as e:
            logger.error(f"NewsAPI HTTP error: {e.status} - {e.message}")
        except Exception as e:
            logger.error(f"NewsAPI search error: {e}")
        finally:
            if not client:
                await async_client.close()
        return results

    @staticmethod
    async def search_stackexchange(
        query: str,
        num_results: int = 10,
        client: Optional[aiohttp.ClientSession] = None,
    ) -> List[Dict[str, str]]:
        logger = logging.getLogger(__name__)
        logger.info(f"Starting Stack Exchange search for: {query} on Stack Overflow")
        results = []
        params = {
            "q": query,
            "order": "desc",
            "sort": "relevance",
            "site": "stackoverflow",
            "pagesize": num_results,
            "filter": "!nKzQUR693x",
        }
        if AggregatedSearchTool.STACKEXCHANGE_KEY:
            params["key"] = AggregatedSearchTool.STACKEXCHANGE_KEY
        async_client = client or await AggregatedSearchTool.get_async_client()
        try:
            async with async_client.get(
                AggregatedSearchTool.STACKEXCHANGE_API_URL, params=params
            ) as response:
                response.raise_for_status()
                stack_data = await response.json()
                items = stack_data.get("items", [])
                for item in items:
                    results.append(
                        AggregatedSearchTool._format_result(
                            title=item.get("title", "N/A"),
                            link=item.get("link", "#"),
                            snippet=item.get("excerpt", item.get("body_markdown", ""))[
                                :300
                            ],
                        )
                    )
                    if len(results) >= num_results:
                        break
                logger.info(
                    f"Stack Exchange search completed. Found {len(results)} results."
                )
        except aiohttp.ClientResponseError as e:
            logger.error(f"Stack Exchange API HTTP error: {e.status} - {e.message}")
        except Exception as e:
            logger.error(f"Stack Exchange search error: {e}")
        finally:
            if not client:
                await async_client.close()
        return results

    @staticmethod
    async def search_github_repos(
        query: str,
        num_results: int = 10,
        client: Optional[aiohttp.ClientSession] = None,
    ) -> List[Dict[str, str]]:
        logger = logging.getLogger(__name__)
        logger.info(f"Starting GitHub repository search for: {query}")
        results = []
        headers = {"Accept": "application/vnd.github.v3+json"}
        if AggregatedSearchTool.GITHUB_TOKEN:
            headers["Authorization"] = f"token {AggregatedSearchTool.GITHUB_TOKEN}"
        else:
            logger.warning(
                "GitHub Token not configured. Search may be rate-limited. Consider adding a token."
            )
        params = {
            "q": query,
            "per_page": num_results,
            "sort": "stars",
            "order": "desc",
        }
        async_client = client or await AggregatedSearchTool.get_async_client()
        try:
            async with async_client.get(
                AggregatedSearchTool.GITHUB_API_SEARCH_REPOS_URL,
                headers=headers,
                params=params,
            ) as response:
                response.raise_for_status()
                github_data = await response.json()
                items = github_data.get("items", [])
                for item in items:
                    results.append(
                        AggregatedSearchTool._format_result(
                            title=item.get("full_name", "N/A"),
                            link=item.get("html_url", "#"),
                            snippet=item.get("description", ""),
                        )
                    )
                    if len(results) >= num_results:
                        break
                logger.info(f"GitHub search completed. Found {len(results)} results.")
        except aiohttp.ClientResponseError as e:
            logger.error(f"GitHub API HTTP error: {e.status} - {e.message}")
        except Exception as e:
            logger.error(f"GitHub search error: {e}")
        finally:
            if not client:
                await async_client.close()
        return results

    @staticmethod
    async def search_openlibrary(
        query: str,
        num_results: int = 10,
        client: Optional[aiohttp.ClientSession] = None,
    ) -> List[Dict[str, str]]:
        logger = logging.getLogger(__name__)
        logger.info(f"Starting Open Library search for: {query}")
        results = []
        params = {
            "q": query,
            "limit": num_results,
            "fields": "key,title,author_name,first_sentence_text,first_publish_year",
        }
        async_client = client or await AggregatedSearchTool.get_async_client()
        try:
            async with async_client.get(
                AggregatedSearchTool.OPENLIBRARY_SEARCH_URL, params=params
            ) as response:
                response.raise_for_status()
                library_data = await response.json()
                docs = library_data.get("docs", [])
                for doc in docs:
                    title = doc.get("title", "N/A")
                    author_names = doc.get("author_name", [])
                    if author_names:
                        title = f"{title} by {', '.join(author_names)}"
                    snippet_parts = []
                    if doc.get("first_publish_year"):
                        snippet_parts.append(f"Pub: {doc.get('first_publish_year')}")
                    sentences = doc.get("first_sentence_text")
                    if sentences:
                        snippet_parts.append(
                            sentences[0]
                            if isinstance(sentences, list) and sentences
                            else str(sentences)
                        )
                    results.append(
                        AggregatedSearchTool._format_result(
                            title=title,
                            link=(
                                f"https://openlibrary.org{doc.get('key', '')}"
                                if doc.get("key")
                                else "#"
                            ),
                            snippet=(". ".join(filter(None, snippet_parts))),
                        )
                    )
                    if len(results) >= num_results:
                        break
                logger.info(
                    f"Open Library search completed. Found {len(results)} results."
                )
        except aiohttp.ClientResponseError as e:
            logger.error(f"Open Library API HTTP error: {e.status} - {e.message}")
        except Exception as e:
            logger.error(f"Open Library search error: {e}")
        finally:
            if not client:
                await async_client.close()
        return results

    @staticmethod
    async def search_duckduckgo(
        query: str, num_results: int = 10
    ) -> List[Dict[str, str]]:
        logger = logging.getLogger(__name__)
        logger.info(f"Starting DuckDuckGo search for: {query}")
        results = []
        # DDGS now supports async iteration in v8+
        async with DDGS() as ddgs:
            async for r in ddgs.text(keywords=query, max_results=num_results):
                results.append(
                    AggregatedSearchTool._format_result(
                        title=str(r.get("title", "N/A")),
                        link=str(r.get("href", "#")),
                        snippet=str(r.get("body", "")),
                    )
                )
                if len(results) >= num_results:
                    break
        logger.info(f"DuckDuckGo search completed. Found {len(results)} results.")
        return results

    @staticmethod
    async def aggregated_search(
        query: str, category: str = "all"
    ) -> Dict[str, List[Dict[str, str]]]:
        """Performs an aggregated search across multiple services based on category.

        Args:
            query (str): The search query string.
            category (str): The service category (web, academic, news, code, books, q&a, or 'all').

        Returns:
            Dict[str, List[Dict[str, str]]]: Mapping of service name to list of result dicts.
        """
        # For now, only implement DuckDuckGo search for 'web' and 'all' categories
        logger = logging.getLogger(__name__)
        results = {}
        if category in ("web", "all"):
            try:
                with DDGS() as ddgs:
                    ddg_results = []
                    for r in ddgs.text(
                        query,
                        region="wt-wt",
                        safesearch="Moderate",
                        max_results=10,
                    ):
                        ddg_results.append(
                            AggregatedSearchTool._format_result(
                                title=r.get("title", "N/A"),
                                link=r.get("href", r.get("url", "#")),
                                snippet=r.get("body", r.get("snippet", "")),
                            )
                        )
                    results["duckduckgo"] = ddg_results
            except Exception as e:
                logger.error(f"DuckDuckGo search error: {e}")
                results["duckduckgo"] = [
                    {
                        "title": "DuckDuckGo search error",
                        "link": "#",
                        "snippet": str(e),
                    }
                ]
        # Optionally, add stubs for other categories
        return results

    # Optionally, add a sync wrapper for LLM tools
    @staticmethod
    def aggregated_search_sync(
        query: str, category: str = "all"
    ) -> Dict[str, List[Dict[str, str]]]:
        """Synchronous wrapper for aggregated_search (for LLM tool compatibility)."""
        return asyncio.run(AggregatedSearchTool.aggregated_search(query, category))
