"""
Intelligent web crawling tool - LLM-guided multi-page crawling.

This tool uses LLM decision-making to intelligently navigate websites,
following relevant links and gathering comprehensive information.
"""

from typing import Annotated, Any

from scrapy.crawler import CrawlerProcess

from airunner.components.llm.core.tool_registry import tool, ToolCategory
from airunner.components.tools.scrapy.spiders.llm_guided_spider import (
    LLMGuidedSpider,
)
from airunner.components.tools.scrapy.llm_crawler_controller import (
    LLMCrawlerController,
)
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


@tool(
    name="intelligent_crawl",
    category=ToolCategory.RESEARCH,
    description=(
        "Intelligently crawl a website by following relevant links using LLM decision-making. "
        "Starts from a seed URL and recursively visits pages that are relevant to your research goal. "
        "The LLM analyzes each page's content and decides which links to follow, ensuring comprehensive "
        "yet focused information gathering. Returns aggregated content from all visited pages. "
        "Use this when you need to gather in-depth information from multiple related web pages."
    ),
    return_direct=False,
    requires_api=True,
)
def intelligent_crawl(
    start_url: Annotated[
        str,
        "The initial URL to start crawling from (e.g., 'https://example.com/article')",
    ],
    research_goal: Annotated[
        str,
        "Description of what you're researching (helps guide link selection)",
    ],
    max_pages: Annotated[
        int, "Maximum number of pages to crawl (default: 10, max: 20)"
    ] = 10,
    max_depth: Annotated[
        int,
        "Maximum crawl depth / links to follow from start page (default: 2, max: 3)",
    ] = 2,
    api: Any = None,
) -> str:
    """
    Intelligently crawl a website using LLM-guided link selection.

    This tool:
    1. Starts at the given URL
    2. Extracts content and finds all links on the page
    3. Uses LLM to determine which links are most relevant
    4. Follows selected links and repeats the process
    5. Stops when enough information is gathered or limits are reached
    6. Returns aggregated content from all visited pages

    Args:
        start_url: URL to start crawling from
        research_goal: What you're researching (guides link selection)
        max_pages: Maximum pages to crawl (1-20)
        max_depth: Maximum depth to crawl (1-3)
        api: API instance (injected automatically)

    """
    logger.info(
        f"intelligent_crawl: url={start_url}, goal='{research_goal}', "
        f"max_pages={max_pages}, max_depth={max_depth}"
    )

    # Validate parameters
    max_pages = max(1, min(max_pages, 20))  # Clamp to 1-20
    max_depth = max(1, min(max_depth, 3))  # Clamp to 1-3

    if not api:
        return "Error: API not available for intelligent crawling"

    try:
        # Create a simple LLM invocation function for the controller
        def llm_invoke(prompt: str) -> str:
            """Invoke LLM with a prompt and return response."""
            try:
                import uuid
                from airunner.components.llm.managers.llm_request import (
                    LLMRequest,
                )
                from airunner.enums import LLMActionType
                from airunner.utils.application.signal_mediator import (
                    SignalMediator,
                )

                # Create a request optimized for decision-making
                llm_request = LLMRequest.for_action(LLMActionType.DECISION)
                llm_request.max_new_tokens = 500  # Enough for JSON response
                llm_request.temperature = 0.3  # More deterministic
                llm_request.do_stream = (
                    False  # Non-streaming for synchronous response
                )

                # Generate unique request ID for correlation
                request_id = str(uuid.uuid4())

                # Register pending request with signal mediator
                mediator = SignalMediator()
                mediator.register_pending_request(request_id)

                logger.debug(
                    f"Sending LLM crawler decision request with id={request_id}"
                )

                # Send the LLM request
                api.llm.send_request(
                    prompt=prompt,
                    llm_request=llm_request,
                    action=LLMActionType.DECISION,
                    do_tts_reply=False,  # No TTS for crawler decisions
                    request_id=request_id,
                )

                # Wait for response with 30 second timeout
                response_data = mediator.wait_for_response(
                    request_id, timeout=30.0
                )

                # Clean up pending request
                mediator.unregister_pending_request(request_id)

                if response_data and "response" in response_data:
                    # Extract the message from the LLMResponse object
                    llm_response = response_data["response"]
                    message = getattr(llm_response, "message", "")

                    if message:
                        logger.debug(
                            f"Received LLM crawler decision: {message[:100]}..."
                        )
                        return message
                    else:
                        logger.warning("LLM response had no message content")
                        raise ValueError("Empty LLM response")
                else:
                    logger.warning(
                        f"LLM request timed out or failed for request_id={request_id}"
                    )
                    raise TimeoutError("LLM request timeout")

            except Exception as e:
                logger.error(f"LLM invocation failed: {e}", exc_info=True)
                # Return a fallback decision using heuristic
                return """
                {
                  "page_relevant": false,
                  "relevance_explanation": "Error during LLM invocation - using fallback",
                  "follow_urls": [],
                  "link_rationale": "Error fallback",
                  "sufficient_info": true,
                  "next_steps": "Stopping due to error"
                }
                """

        # Create the LLM controller
        controller = LLMCrawlerController(
            llm_invoke_func=llm_invoke,
            research_goal=research_goal,
            max_links_per_page=3,
        )

        # Collected results
        collected_pages = []

        # Create decision callback that uses the controller
        def decision_callback(
            page_data, research_goal, pages_scraped, max_pages
        ):
            """Callback invoked by spider for each page."""
            # Store the page data
            collected_pages.append(page_data)

            # Get LLM decision
            decision = controller.make_decision(
                page_data=page_data,
                research_goal=research_goal,
                pages_scraped=pages_scraped,
                max_pages=max_pages,
            )

            return decision

        # Configure Scrapy settings
        settings = {
            "LOG_LEVEL": "WARNING",  # Reduce Scrapy noise
            "ROBOTSTXT_OBEY": True,
            "CONCURRENT_REQUESTS": 1,
            "DOWNLOAD_DELAY": 1.0,
            "DEPTH_LIMIT": max_depth,
            "CLOSESPIDER_PAGECOUNT": max_pages,
            "CLOSESPIDER_TIMEOUT": 300,  # 5 minutes max
        }

        # Create and configure the crawler
        process = CrawlerProcess(settings)

        # Run the spider
        process.crawl(
            LLMGuidedSpider,
            start_url=start_url,
            decision_callback=decision_callback,
            research_goal=research_goal,
            max_pages=max_pages,
            max_depth=max_depth,
        )

        # Start crawling (blocks until complete)
        logger.info(f"Starting intelligent crawl of {start_url}")
        process.start()

        # Format results
        if not collected_pages:
            return f"No pages were successfully crawled from {start_url}"

        # Aggregate content from all pages
        result_text = f"# Intelligent Crawl Results\n\n"
        result_text += f"**Research Goal:** {research_goal}\n"
        result_text += f"**Start URL:** {start_url}\n"
        result_text += f"**Pages Crawled:** {len(collected_pages)}\n\n"
        result_text += "---\n\n"

        for i, page in enumerate(collected_pages, 1):
            metadata = page.get("metadata", {})
            content = page.get("content", "")
            url = page.get("url", "unknown")

            result_text += (
                f"## Page {i}: {metadata.get('title', 'Untitled')}\n\n"
            )
            result_text += f"**URL:** {url}\n"
            if metadata.get("author"):
                result_text += f"**Author:** {metadata['author']}\n"
            if metadata.get("publish_date"):
                result_text += f"**Published:** {metadata['publish_date']}\n"
            result_text += f"\n{content}\n\n"
            result_text += "---\n\n"

        # Add stats
        stats = controller.get_stats()
        result_text += f"\n**Crawl Statistics:**\n"
        result_text += f"- Pages analyzed: {stats['pages_analyzed']}\n"
        result_text += f"- Relevant pages: {stats['relevant_pages']}\n"
        result_text += f"- Relevance rate: {stats['relevance_rate']:.1%}\n"
        result_text += f"- Links followed: {stats['total_links_followed']}\n"

        logger.info(
            f"Intelligent crawl complete: {len(collected_pages)} pages, "
            f"{stats['relevant_pages']} relevant"
        )

        return result_text

    except Exception as e:
        logger.error(f"Intelligent crawl failed: {e}", exc_info=True)
        return f"Error during intelligent crawl: {str(e)}"
