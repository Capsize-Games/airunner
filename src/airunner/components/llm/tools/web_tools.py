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
        "Scrape content from a website URL and extract the text. "
        "Removes scripts, styles, navigation, and footer elements. "
        "Optionally use CSS selectors to target specific content. "
        "Use this to read articles, documentation, or web page content."
    ),
    return_direct=False,
    requires_api=False,
)
def scrape_website(
    url: Annotated[str, "Website URL to scrape content from"],
    selector: Annotated[
        str,
        "Optional CSS selector to target specific elements (e.g., '.article-content', '#main')",
    ] = "",
) -> str:
    """Scrape content from a website.

    Extract text content from web pages for analysis or storage.
    Can optionally use CSS selectors to target specific elements.

    Args:
        url: Website URL to scrape
        selector: Optional CSS selector to target specific content

    Returns:
        Scraped content or error message
    """
    logger.info(f"Scraping: {url} (selector: {selector or 'none'})")

    try:
        import requests
        from bs4 import BeautifulSoup

        # Set headers to mimic a browser
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
        }

        # Fetch the page with timeout
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.content, "html.parser")

        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer"]):
            element.decompose()

        # Extract content based on selector
        if selector:
            elements = soup.select(selector)
            if elements:
                text = "\n\n".join(
                    elem.get_text(strip=True) for elem in elements
                )
            else:
                return f"No elements found matching selector: {selector}"
        else:
            # Try common content containers first
            main_content = (
                soup.find("main")
                or soup.find("article")
                or soup.find("div", class_="content")
                or soup.find("div", id="content")
                or soup.body
            )
            if main_content:
                text = main_content.get_text(separator="\n", strip=True)
            else:
                text = soup.get_text(separator="\n", strip=True)

        # Clean up whitespace
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        clean_text = "\n".join(lines)

        # Limit output length
        max_length = 5000
        if len(clean_text) > max_length:
            clean_text = clean_text[:max_length] + "\n\n[Content truncated...]"

        logger.info(f"✓ Scraped {len(clean_text)} characters from {url}")
        return clean_text

    except requests.exceptions.Timeout:
        return f"Error: Request timed out for {url}"
    except requests.exceptions.ConnectionError:
        return f"Error: Could not connect to {url}"
    except requests.exceptions.HTTPError as e:
        return f"Error: HTTP {e.response.status_code} for {url}"
    except Exception as e:
        logger.error(f"Web scraping error: {e}", exc_info=True)
        return f"Error scraping website: {str(e)}"
