"""
Web search and scraping tools.

Provides tools for searching the internet via DuckDuckGo and
scraping content from websites using BeautifulSoup.
"""

import time
from typing import Annotated

from airunner.components.llm.core.tool_registry import tool, ToolCategory
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

# Rate limiting for DuckDuckGo searches
_last_search_time = 0
_SEARCH_COOLDOWN = 2.0  # seconds between searches


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
    defer_loading=False,  # Essential tool - always available
    keywords=["internet", "google", "duckduckgo", "online", "web", "find"],
    input_examples=[
        {"query": "latest news about artificial intelligence"},
        {"query": "how to install Python on Ubuntu"},
        {"query": "weather forecast for New York"},
    ],
)
def search_web(
    query: Annotated[str, "Search query to look up on the internet"],
) -> str:
    """Search the internet for information using DuckDuckGo.

    Args:
        query: Search query

    """
    global _last_search_time

    # Check if DuckDuckGo search is allowed
    from airunner.components.application.gui.dialogs.privacy_consent_dialog import (
        is_duckduckgo_allowed,
    )
    if not is_duckduckgo_allowed():
        logger.info("Web search disabled by privacy settings")
        return {
            "results": [],
            "summary": "Web search is disabled in privacy settings. "
            "You can enable it in Preferences → Privacy & Security → External Services."
        }

    try:
        # Rate limiting: wait if we searched too recently
        time_since_last = time.time() - _last_search_time
        if time_since_last < _SEARCH_COOLDOWN:
            wait_time = _SEARCH_COOLDOWN - time_since_last
            logger.info(
                f"Rate limiting: waiting {wait_time:.1f}s before search"
            )
            time.sleep(wait_time)

        _last_search_time = time.time()

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

        # Return structured results dict for programmatic consumption
        ddg_results = results.get("duckduckgo", []) if results else []
        logger.info(f"Got {len(ddg_results)} DuckDuckGo results")

        if not ddg_results:
            logger.warning(f"Empty DuckDuckGo results list for: {query}")
            return {"results": []}

        # Provide both raw results and a human-readable summary
        formatted = f"Web search results for '{query}':\n\n"
        for i, result in enumerate(ddg_results[:5], 1):
            title = result.get("title", "N/A")
            link = result.get("link", "#")
            snippet = result.get("snippet", "")[:200]
            formatted += f"{i}. {title}\n"
            formatted += f"   URL: {link}\n"
            if snippet:
                formatted += f"   {snippet}...\n"
            formatted += "\n"

        # Add instructions that support continued tool use
        formatted += "\n" + "="*60 + "\n"
        formatted += "📝 NEXT STEPS: You can:\n"
        formatted += "- Use `scrape_website` on a URL to get full article content\n"
        formatted += "- Use `search_web` again with a different query for more info\n"
        formatted += "- Use `create_research_document` to save findings\n"
        formatted += "- Or respond directly if you have enough information\n"
        formatted += "="*60 + "\n"

        logger.info(f"✓ Formatted {len(ddg_results[:5])} search results")
        return {"results": ddg_results, "summary": formatted}
    except Exception as e:
        logger.error(f"Web search error: {e}", exc_info=True)
        return f"Error searching web: {str(e)}"


@tool(
    name="search_news",
    category=ToolCategory.SEARCH,
    description=(
        "Search for recent news articles and current events using DuckDuckGo News. "
        "Returns news articles with titles, URLs, snippets, sources, and dates. "
        "ALWAYS use this for current events, recent decisions, breaking news, or anything time-sensitive. "
        "Better than search_web for: politics, government actions, recent appointments, etc."
    ),
    return_direct=False,
    requires_api=False,
)
def search_news(
    query: Annotated[
        str,
        "News search query - focus on current events and recent information",
    ],
) -> str:
    """Search for recent news articles using DuckDuckGo News.

    This tool is specifically designed for current events and should be used when:
    - User asks about recent events ("recent", "latest", "new")
    - Political news, government decisions, appointments
    - Breaking news or time-sensitive information
    - Anything that happened in the last days/weeks/months

    Args:
        query: News search query

    """
    global _last_search_time

    # Check if DuckDuckGo search is allowed
    from airunner.components.application.gui.dialogs.privacy_consent_dialog import (
        is_duckduckgo_allowed,
    )
    if not is_duckduckgo_allowed():
        logger.info("News search disabled by privacy settings")
        return {
            "results": [],
            "summary": "Web search is disabled in privacy settings. "
            "You can enable it in Preferences → Privacy & Security → External Services."
        }

    try:
        # Rate limiting: wait if we searched too recently
        time_since_last = time.time() - _last_search_time
        if time_since_last < _SEARCH_COOLDOWN:
            wait_time = _SEARCH_COOLDOWN - time_since_last
            logger.info(
                f"Rate limiting: waiting {wait_time:.1f}s before news search"
            )
            time.sleep(wait_time)

        _last_search_time = time.time()

        from airunner.components.tools.search_providers.duckduckgo_provider import (
            DuckDuckGoProvider,
        )
        import asyncio

        logger.info(f"📰 Searching news for: {query}")

        # Use DuckDuckGo news search
        provider = DuckDuckGoProvider()
        results = asyncio.run(provider.news_search(query, num_results=10))

        logger.info(f"Got {len(results)} news results")

        if not results:
            logger.warning(f"No news results for: {query}")
            return {"results": []}

        # Format top 7 results and return structured dict
        formatted = f"Recent news articles for '{query}':\n\n"
        for i, result in enumerate(results[:7], 1):
            title = result.get("title", "N/A")
            link = result.get("link", "#")
            snippet = result.get("snippet", "")[:250]
            source = result.get("source", "Unknown source")
            date = result.get("date", "")

            formatted += f"{i}. {title}\n"
            formatted += f"   Source: {source}"
            if date:
                formatted += f" | Date: {date}"
            formatted += f"\n   URL: {link}\n"
            if snippet:
                formatted += f"   {snippet}...\n"
            formatted += "\n"

        # Add instructions that support continued tool use
        formatted += "\n" + "="*60 + "\n"
        formatted += "📝 NEXT STEPS: You can:\n"
        formatted += "- Use `scrape_website` on a URL to get full article content\n"
        formatted += "- Use `search_news` again with a different query for more info\n"
        formatted += "- Use `create_research_document` to save findings\n"
        formatted += "- Or respond directly if you have enough information\n"
        formatted += "="*60 + "\n"

        logger.info(f"✓ Formatted {len(results[:7])} news results")
        return {"results": results, "summary": formatted}
    except Exception as e:
        logger.error(f"News search error: {e}", exc_info=True)
        return f"Error searching news: {str(e)}"


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
) -> dict:
    """Scrape and extract clean content with metadata from a website.

    Uses Trafilatura for intelligent content extraction that automatically
    identifies and extracts the main content while removing navigation,
    ads, footers, and other boilerplate elements.

    Args:
        url: Website URL to scrape (e.g., "https://example.com/article")

    """
    logger.info(f"Scraping: {url}")

    try:
        from airunner.components.tools.web_content_extractor import (
            WebContentExtractor,
        )

        # Use new method that extracts both content and metadata
        result = WebContentExtractor.fetch_and_extract_with_metadata(
            url, use_cache=True
        )

        if result and result.get("content"):
            logger.info(
                f"✓ Extracted {len(result['content'])} characters from {url}"
            )
            logger.info(f"  Title: {result.get('title', 'N/A')}")
            # Add explicit instructions to answer the user's question
            result["_instructions"] = (
                "📝 IMPORTANT: Use this content to answer the user's original question. "
                "Optionally, use record_knowledge() to save key facts for future reference."
            )
            return result
        else:
            return {
                "content": None,
                "error": (
                    f"Could not extract content from {url}. "
                    "The page may be empty, require JavaScript, or be blocking scrapers."
                ),
            }

    except Exception as e:
        logger.error(f"Web scraping error for {url}: {e}", exc_info=True)
        return {"content": None, "error": f"Error scraping {url}: {str(e)}"}
