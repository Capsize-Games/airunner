"""Web searching and scraping tools."""

import logging
from typing import Callable

from langchain.tools import tool

from airunner.enums import SignalCode


class WebTools:
    """Mixin class providing web search and scraping tools."""


    def search_web_tool(self) -> Callable:
        """Search the web for information."""

        @tool
        def search_web(query: str) -> str:
            """Search the internet for information.

            Args:
                query: Search query

            Returns:
                Search results
            """
            try:
                self.emit_signal(
                    SignalCode.SEARCH_WEB_SIGNAL, {"query": query}
                )
                return f"Searching for: {query}"
            except Exception as e:
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
