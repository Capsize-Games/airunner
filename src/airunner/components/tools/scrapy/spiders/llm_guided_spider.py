"""
LLM-Guided Spider for intelligent web crawling.

This spider uses external LLM decision-making to determine which links
to follow during crawling. Instead of blindly following all links, it
yields page data to an external controller (LLM) and waits for decisions
on which links are worth following.
"""

import scrapy
from typing import Callable, Optional, Set, Dict, List

from airunner.components.tools.web_content_extractor import WebContentExtractor
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class LLMGuidedSpider(scrapy.Spider):
    """
    Scrapy spider that uses LLM decision-making for intelligent crawling.

    This spider:
    1. Scrapes a web page
    2. Extracts clean content + links
    3. Yields page data to external decision callback
    4. Receives list of URLs to follow from callback
    5. Continues crawling selected URLs
    """

    name = "llm_guided"

    def __init__(
        self,
        start_url: str,
        decision_callback: Optional[Callable] = None,
        research_goal: str = "",
        max_pages: int = 20,
        max_depth: int = 3,
        *args,
        **kwargs,
    ):
        """
        Initialize the LLM-guided spider.

        Args:
            start_url: Initial URL to start crawling from
            decision_callback: Function that receives page data and returns
                             dict with 'follow_urls' list
            research_goal: Description of what we're researching (for context)
            max_pages: Maximum number of pages to crawl
            max_depth: Maximum crawl depth
        """
        super().__init__(*args, **kwargs)

        self.start_urls = [start_url]
        self.decision_callback = decision_callback
        self.research_goal = research_goal
        self.max_pages = max_pages
        self.max_depth = max_depth

        # State tracking
        self.visited: Set[str] = set()
        self.pages_scraped: int = 0
        self.collected_content: List[Dict] = []

        # Configure custom settings
        self.custom_settings = {
            "DEPTH_LIMIT": max_depth,
            "CLOSESPIDER_PAGECOUNT": max_pages,
        }

        logger.info(
            f"LLMGuidedSpider initialized: goal='{research_goal}', "
            f"max_pages={max_pages}, max_depth={max_depth}"
        )

    def parse(self, response):
        """
        Parse a web page: extract content, get LLM decision, follow links.

        This is the main parsing method called for each crawled page.
        """
        url = response.url
        self.visited.add(url)
        self.pages_scraped += 1

        logger.info(
            f"Parsing page {self.pages_scraped}/{self.max_pages}: {url}"
        )

        # Extract content and links
        page_data = self._extract_page_data(response)

        if not page_data:
            logger.warning(f"Failed to extract data from {url}")
            return

        # Store the collected content
        self.collected_content.append(page_data)

        # Get LLM decision on which links to follow
        if self.decision_callback and self.pages_scraped < self.max_pages:
            try:
                decision = self.decision_callback(
                    page_data=page_data,
                    research_goal=self.research_goal,
                    pages_scraped=self.pages_scraped,
                    max_pages=self.max_pages,
                )

                # Extract URLs to follow from decision
                urls_to_follow = decision.get("follow_urls", [])

                logger.info(
                    f"LLM decision: follow {len(urls_to_follow)} links, "
                    f"sufficient_info={decision.get('sufficient_info', False)}"
                )

                # Stop crawling if LLM says we have enough info
                if decision.get("sufficient_info", False):
                    logger.info(
                        "LLM indicated sufficient information gathered - stopping crawl"
                    )
                    return

                # Follow approved URLs
                for link_url in urls_to_follow[:3]:  # Limit to top 3
                    if link_url not in self.visited:
                        logger.info(f"Following LLM-selected link: {link_url}")
                        yield scrapy.Request(
                            link_url,
                            callback=self.parse,
                            errback=self.errback_httpbin,
                            dont_filter=False,  # Still respect Scrapy's duplicate filter
                        )

            except Exception as e:
                logger.error(f"Error in decision callback: {e}", exc_info=True)

        # Yield the scraped page data
        yield page_data

    def _extract_page_data(self, response) -> Optional[Dict]:
        """
        Extract content, links, and metadata from a response.

        Args:
            response: Scrapy response object

        Returns:
            Dictionary with content, links, metadata, or None if extraction fails
        """
        try:
            url = response.url
            html_content = response.text

            # Use WebContentExtractor to get content + links
            result = WebContentExtractor.extract_with_links(
                url, content=html_content
            )

            if not result:
                logger.warning(f"WebContentExtractor returned None for {url}")
                return None

            # Add URL and depth info
            result["url"] = url
            result["depth"] = response.meta.get("depth", 0)
            result["page_number"] = self.pages_scraped

            logger.info(
                f"Extracted {len(result['content'])} chars content, "
                f"{len(result['links'])} links from {url}"
            )

            return result

        except Exception as e:
            logger.error(
                f"Error extracting page data from {response.url}: {e}",
                exc_info=True,
            )
            return None

    def errback_httpbin(self, failure):
        """Handle request failures."""
        logger.error(f"Request failed: {repr(failure)}")

    def closed(self, reason):
        """Called when spider closes."""
        logger.info(
            f"Spider closed: {reason}. "
            f"Scraped {self.pages_scraped} pages, "
            f"collected {len(self.collected_content)} page data items"
        )
