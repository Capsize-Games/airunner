"""Web searching and scraping tools."""

from typing import Callable

from langchain.tools import tool



class WebTools:
    """Mixin class providing web search and scraping tools."""

    def search_web_tool(self) -> Callable:
        """Search the web for information using DuckDuckGo."""

        @tool
        def search_web(query: str) -> str:
            """Search the internet for information using DuckDuckGo.

            Args:
                query: Search query

            Returns:
                Formatted search results from DuckDuckGo
            """
            try:
                # Import the aggregated search tool
                from airunner.components.tools.search_tool import (
                    AggregatedSearchTool,
                )

                self.logger.info(f"🔍 Searching web for: {query}")

                # Use DuckDuckGo search (web category)
                results = AggregatedSearchTool.aggregated_search_sync(
                    query, category="web"
                )

                self.logger.info(
                    f"Search results keys: {results.keys() if results else 'None'}"
                )

                # Format results
                if not results or "duckduckgo" not in results:
                    self.logger.warning(
                        f"No results dict or missing duckduckgo key for: {query}"
                    )
                    return f"No search results available for: {query}"

                ddg_results = results["duckduckgo"]
                self.logger.info(f"Got {len(ddg_results)} DuckDuckGo results")

                if not ddg_results:
                    self.logger.warning(
                        f"Empty DuckDuckGo results list for: {query}"
                    )
                    return f"No search results available for: {query}"

                # Format top 5 results
                formatted = f"Web search results for '{query}':\n\n"
                for i, result in enumerate(ddg_results[:5], 1):
                    title = result.get("title", "N/A")
                    link = result.get("link", "#")
                    snippet = result.get("snippet", "")[
                        :200
                    ]  # Limit snippet length
                    formatted += f"{i}. {title}\n"
                    formatted += f"   URL: {link}\n"
                    if snippet:
                        formatted += f"   {snippet}...\n"
                    formatted += "\n"

                self.logger.info(
                    f"✓ Formatted {len(ddg_results[:5])} search results"
                )
                return formatted
            except Exception as e:
                self.logger.error(f"Web search error: {e}", exc_info=True)
                return f"Error searching web: {str(e)}"

        return search_web

    def web_scraper_tool(self) -> Callable:
        """Scrape content from websites using BeautifulSoup."""

        @tool
        def scrape_website(url: str, selector: str = "") -> str:
            """Scrape content from a website.

            Extract text content from web pages for analysis or storage.
            Can optionally use CSS selectors to target specific elements.

            Args:
                url: Website URL to scrape
                selector: Optional CSS selector to target specific content

            Returns:
                Scraped content or error message
            """
            self.logger.info(
                f"Scraping: {url} (selector: {selector or 'none'})"
            )

            try:
                import requests
                from bs4 import BeautifulSoup

                # Set headers to mimic a browser
                headers = {
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
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
                        return (
                            f"No elements found matching selector: {selector}"
                        )
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
                        text = main_content.get_text(
                            separator="\n", strip=True
                        )
                    else:
                        text = soup.get_text(separator="\n", strip=True)

                # Clean up whitespace
                lines = [
                    line.strip() for line in text.splitlines() if line.strip()
                ]
                cleaned_text = "\n".join(lines)

                # Truncate if too long (keep first 10000 chars)
                if len(cleaned_text) > 10000:
                    cleaned_text = (
                        cleaned_text[:10000] + "\n\n[Content truncated...]"
                    )

                self.logger.info(
                    f"Successfully scraped {len(cleaned_text)} characters"
                )
                return cleaned_text

            except Exception as e:
                error_msg = f"Error scraping website: {str(e)}"
                self.logger.error(error_msg)
                return error_msg

        return scrape_website
