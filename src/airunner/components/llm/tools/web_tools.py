"""
Web search and scraping tools.

Provides tools for searching the internet via DuckDuckGo and
scraping content from websites using BeautifulSoup.
"""

import logging
from typing import Annotated

from airunner.components.llm.core.tool_registry import tool, ToolCategory

logger = logging.getLogger(__name__)


@tool(
    name="search_web",
    category=ToolCategory.SEARCH,
    description=(
        "Search the internet for information using DuckDuckGo. "
        "Returns top search results with titles, URLs, and snippets. "
        "Use this to find current information, websites, or answers to questions."
    ),
    return_direct=False,
    requires_api=False,
)
def search_web(
    query: Annotated[str, "Search query to look up on the internet"],
) -> str:
    """Search the internet for information using DuckDuckGo.

    Args:
        query: Search query

    Returns:
        Formatted search results from DuckDuckGo
    """
    try:
        from airunner.components.tools.search_tool import (
            AggregatedSearchTool,
        )

        logger.info(f"🔍 Searching web for: {query}")

        # Use DuckDuckGo search (web category)
        results = AggregatedSearchTool.aggregated_search_sync(
            query, category="web"
        )

        logger.info(
            f"Search results keys: {results.keys() if results else 'None'}"
        )

        # Format results
        if not results or "duckduckgo" not in results:
            logger.warning(
                f"No results dict or missing duckduckgo key for: {query}"
            )
            return f"No search results available for: {query}"

        ddg_results = results["duckduckgo"]
        logger.info(f"Got {len(ddg_results)} DuckDuckGo results")

        if not ddg_results:
            logger.warning(f"Empty DuckDuckGo results list for: {query}")
            return f"No search results available for: {query}"

        # Format top 5 results
        formatted = f"Web search results for '{query}':\n\n"
        for i, result in enumerate(ddg_results[:5], 1):
            title = result.get("title", "N/A")
            link = result.get("link", "#")
            snippet = result.get("snippet", "")[:200]  # Limit snippet length
            formatted += f"{i}. {title}\n"
            formatted += f"   URL: {link}\n"
            if snippet:
                formatted += f"   {snippet}...\n"
            formatted += "\n"

        logger.info(f"✓ Formatted {len(ddg_results[:5])} search results")
        return formatted
    except Exception as e:
        logger.error(f"Web search error: {e}", exc_info=True)
        return f"Error searching web: {str(e)}"


@tool(
    name="scrape_website",
    category=ToolCategory.SEARCH,
    description=(
        "Scrape and extract clean text content from a website URL. "
        "Automatically removes boilerplate, navigation, ads, and footer elements. "
        "Returns only the main content of the page. "
        "Use this to read articles, blog posts, documentation, or any web page content."
    ),
    return_direct=False,
    requires_api=False,
)
def scrape_website(
    url: Annotated[
        str,
        "Website URL to scrape content from (must include http:// or https://)",
    ],
) -> str:
    """Scrape and extract clean content from a website.

    Uses Trafilatura for intelligent content extraction that automatically
    identifies and extracts the main content while removing navigation,
    ads, footers, and other boilerplate elements.

    Args:
        url: Website URL to scrape (e.g., "https://example.com/article")

    Returns:
        Extracted and summarized content, or error message if scraping fails
    """
    logger.info(f"Scraping: {url}")

    try:
        from airunner.components.tools.web_content_extractor import (
            WebContentExtractor,
        )

        # Use WebContentExtractor which uses Trafilatura for smart extraction
        # This automatically handles content detection, boilerplate removal, and summarization
        content = WebContentExtractor.fetch_and_extract(url, use_cache=True)

        if content:
            logger.info(f"✓ Extracted {len(content)} characters from {url}")
            return content
        else:
            return (
                f"Could not extract content from {url}. "
                "The page may be empty, require JavaScript, or be blocking scrapers."
            )

    except Exception as e:
        logger.error(f"Web scraping error for {url}: {e}", exc_info=True)
        return f"Error scraping {url}: {str(e)}"
