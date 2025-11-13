"""
LLM Crawler Controller - Intelligent crawling decisions using LLM.

This controller manages the interaction between the Scrapy spider and the LLM.
It formats prompts, invokes the LLM, and parses decisions about which links to follow.
"""

import json
from typing import Dict, List, Any, Callable
from dataclasses import dataclass

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


@dataclass
class CrawlDecision:
    """Represents an LLM's decision about crawling."""

    page_relevant: bool
    relevance_explanation: str
    follow_urls: List[str]
    link_rationale: str
    sufficient_info: bool
    next_steps: str


class LLMCrawlerController:
    """
    Controls LLM-guided web crawling by making intelligent decisions.

    This controller:
    1. Receives page data from spider
    2. Formats prompt for LLM with context
    3. Invokes LLM to get decision
    4. Parses LLM response
    5. Returns decision to spider
    """

    def __init__(
        self,
        llm_invoke_func: Callable[[str], str],
        research_goal: str,
        max_links_per_page: int = 3,
    ):
        """
        Initialize the LLM crawler controller.

        Args:
            llm_invoke_func: Function that takes a prompt string and returns LLM response
            research_goal: The research objective (used in prompts)
            max_links_per_page: Maximum number of links to select per page
        """
        self.llm_invoke_func = llm_invoke_func
        self.research_goal = research_goal
        self.max_links_per_page = max_links_per_page

        # Track crawl state
        self.pages_analyzed = 0
        self.relevant_pages = 0
        self.total_links_followed = 0

        logger.info(
            f"LLMCrawlerController initialized: goal='{research_goal}', "
            f"max_links_per_page={max_links_per_page}"
        )

    def make_decision(
        self,
        page_data: Dict,
        research_goal: str,
        pages_scraped: int,
        max_pages: int,
    ) -> Dict[str, Any]:
        """
        Make a crawling decision based on page content.

        Args:
            page_data: Dictionary with content, links, metadata from current page
            research_goal: The research objective
            pages_scraped: Number of pages scraped so far
            max_pages: Maximum pages allowed

        Returns:
            Dictionary with decision:
            - follow_urls: List of URLs to crawl next
            - page_relevant: Whether this page was relevant
            - sufficient_info: Whether we have enough information
        """
        self.pages_analyzed += 1

        try:
            # Format the decision prompt
            prompt = self._format_decision_prompt(
                page_data, research_goal, pages_scraped, max_pages
            )

            # Invoke LLM
            logger.info(
                f"Requesting LLM decision for page: {page_data.get('url', 'unknown')}"
            )
            llm_response = self.llm_invoke_func(prompt)

            # Parse LLM response
            decision = self._parse_llm_response(llm_response, page_data)

            # Update stats
            if decision.page_relevant:
                self.relevant_pages += 1
            self.total_links_followed += len(decision.follow_urls)

            logger.info(
                f"Decision: relevant={decision.page_relevant}, "
                f"follow={len(decision.follow_urls)} links, "
                f"sufficient={decision.sufficient_info}"
            )

            return {
                "follow_urls": decision.follow_urls[: self.max_links_per_page],
                "page_relevant": decision.page_relevant,
                "sufficient_info": decision.sufficient_info,
                "rationale": decision.link_rationale,
            }

        except Exception as e:
            logger.error(f"Error making crawl decision: {e}", exc_info=True)
            # Fallback: use heuristic link selection
            return self._heuristic_fallback(
                page_data, pages_scraped, max_pages
            )

    def _format_decision_prompt(
        self,
        page_data: Dict,
        research_goal: str,
        pages_scraped: int,
        max_pages: int,
    ) -> str:
        """
        Format a prompt for the LLM to make crawling decisions.

        Args:
            page_data: Current page data
            research_goal: Research objective
            pages_scraped: Pages scraped so far
            max_pages: Maximum pages allowed

        Returns:
            Formatted prompt string
        """
        content = page_data.get("content", "")
        links = page_data.get("links", [])
        metadata = page_data.get("metadata", {})
        url = page_data.get("url", "unknown")

        # Truncate content for prompt (keep first 1000 chars)
        content_preview = content[:1000] + (
            "..." if len(content) > 1000 else ""
        )

        # Format links section
        links_text = ""
        for i, link in enumerate(links[:10], 1):  # Show max 10 links
            links_text += f"\n{i}. {link['url']}\n"
            links_text += f"   Anchor: {link['anchor_text']}\n"
            links_text += f"   Context: {link['context'][:100]}...\n"

        if len(links) > 10:
            links_text += (
                f"\n... and {len(links) - 10} more links (not shown)\n"
            )

        prompt = f"""You are a research assistant conducting intelligent web crawling.

Research Goal: "{research_goal}"

You just scraped a web page with the following information:

URL: {url}
Title: {metadata.get('title', 'N/A')}
Author: {metadata.get('author', 'N/A')}
Publish Date: {metadata.get('publish_date', 'N/A')}

Page Content ({len(content)} characters total):
---
{content_preview}
---

Available Links on This Page ({len(links)} total):
{links_text if links else "No links found."}

Crawl Progress:
- Pages scraped so far: {pages_scraped}
- Maximum pages allowed: {max_pages}
- Pages remaining: {max_pages - pages_scraped}

Your Task:
Analyze the page content and decide:
1. Is this page relevant to the research goal?
2. Which links (if any) should be followed for more information?
3. Do we have sufficient information to answer the research goal?

Guidelines:
- Select up to {self.max_links_per_page} most promising links
- Prioritize links that directly relate to the research goal
- Consider content quality and source credibility
- If we're running out of pages, be more selective

Respond in JSON format (ONLY JSON, no other text):
{{
  "page_relevant": true/false,
  "relevance_explanation": "brief explanation of why this page is/isn't relevant",
  "follow_urls": ["full_url_1", "full_url_2", "full_url_3"],
  "link_rationale": "why these specific links were chosen",
  "sufficient_info": true/false,
  "next_steps": "what information is still needed (or why we're done)"
}}

Remember: Respond with ONLY the JSON object, no additional text.
"""

        return prompt

    def _parse_llm_response(
        self, llm_response: str, page_data: Dict
    ) -> CrawlDecision:
        """
        Parse LLM JSON response into a CrawlDecision.

        Args:
            llm_response: Raw LLM response text
            page_data: Current page data (for fallback link selection)

        Returns:
            CrawlDecision object
        """
        try:
            # Try to extract JSON from response
            # LLM might include markdown code blocks, so strip those
            response_text = llm_response.strip()

            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                # Remove first and last lines (code block markers)
                response_text = "\n".join(lines[1:-1])

            # Remove any "json" language identifier
            response_text = (
                response_text.replace("```json", "").replace("```", "").strip()
            )

            # Parse JSON
            decision_dict = json.loads(response_text)

            # Validate required fields
            required_fields = [
                "page_relevant",
                "follow_urls",
                "sufficient_info",
            ]
            for field in required_fields:
                if field not in decision_dict:
                    raise ValueError(f"Missing required field: {field}")

            # Create CrawlDecision
            return CrawlDecision(
                page_relevant=bool(decision_dict.get("page_relevant", False)),
                relevance_explanation=str(
                    decision_dict.get("relevance_explanation", "")
                ),
                follow_urls=list(decision_dict.get("follow_urls", []))[
                    : self.max_links_per_page
                ],
                link_rationale=str(decision_dict.get("link_rationale", "")),
                sufficient_info=bool(
                    decision_dict.get("sufficient_info", False)
                ),
                next_steps=str(decision_dict.get("next_steps", "")),
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            logger.debug(f"LLM response was: {llm_response[:500]}")
            # Use heuristic fallback
            return self._heuristic_decision(page_data)
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}", exc_info=True)
            return self._heuristic_decision(page_data)

    def _heuristic_decision(self, page_data: Dict) -> CrawlDecision:
        """
        Make a heuristic decision when LLM parsing fails.

        Uses simple keyword matching and link ranking.
        """
        logger.info("Using heuristic decision (LLM parsing failed)")

        content = page_data.get("content", "").lower()
        links = page_data.get("links", [])

        # Check if content seems relevant (contains research goal keywords)
        research_keywords = self.research_goal.lower().split()
        keyword_count = sum(1 for kw in research_keywords if kw in content)
        page_relevant = keyword_count >= len(research_keywords) / 2

        # Select links based on anchor text relevance
        scored_links = []
        for link in links:
            anchor = link["anchor_text"].lower()
            context = link["context"].lower()
            score = sum(
                1 for kw in research_keywords if kw in anchor or kw in context
            )
            scored_links.append((score, link["url"]))

        # Sort by score and take top N
        scored_links.sort(reverse=True)
        follow_urls = [
            url for score, url in scored_links[: self.max_links_per_page]
        ]

        return CrawlDecision(
            page_relevant=page_relevant,
            relevance_explanation="Heuristic: keyword matching",
            follow_urls=follow_urls,
            link_rationale="Links with highest keyword match",
            sufficient_info=False,  # Never stop with heuristic
            next_steps="Continue crawling (heuristic mode)",
        )

    def _heuristic_fallback(
        self, page_data: Dict, pages_scraped: int, max_pages: int
    ) -> Dict[str, Any]:
        """
        Fallback decision when LLM invocation fails completely.
        """
        decision = self._heuristic_decision(page_data)

        return {
            "follow_urls": decision.follow_urls,
            "page_relevant": decision.page_relevant,
            "sufficient_info": pages_scraped >= max_pages,  # Stop if at limit
            "rationale": "Heuristic fallback due to LLM error",
        }

    def get_stats(self) -> Dict[str, int]:
        """Get crawling statistics."""
        return {
            "pages_analyzed": self.pages_analyzed,
            "relevant_pages": self.relevant_pages,
            "total_links_followed": self.total_links_followed,
            "relevance_rate": self.relevant_pages
            / max(self.pages_analyzed, 1),
        }
