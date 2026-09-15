"""Research-specific post-tool instruction helpers."""

from __future__ import annotations

import re
from typing import List

from langchain_core.messages import BaseMessage


class NodeResearchPostToolHelper:
    """Build research-mode follow-up instructions after tool calls."""

    def scrape_counts(self, tool_messages: List[BaseMessage]) -> tuple[int, int]:
        """Return successful and failed scrape counts."""
        successful_scrapes, failed_scrapes = 0, 0
        for tool_message in tool_messages:
            if getattr(tool_message, "name", None) != "scrape_website":
                continue
            content = str(getattr(tool_message, "content", ""))
            is_error = (
                "error" in content.lower()[:100]
                or "failed" in content.lower()[:100]
                or "could not" in content.lower()[:100]
                or len(content) < 200
            )
            if is_error:
                failed_scrapes += 1
            else:
                successful_scrapes += 1
        return successful_scrapes, failed_scrapes

    @staticmethod
    def search_urls(tool_messages: List[BaseMessage]) -> list[str]:
        """Extract a short URL list from search-result tool messages."""
        search_urls = []
        for tool_message in tool_messages:
            content = str(getattr(tool_message, "content", ""))
            if "http" not in content or "search" not in content.lower():
                continue
            search_urls.extend(re.findall(r'https?://[^\s\]"\'<>]+', content)[:5])
        return search_urls

    def research_instruction(
        self,
        tool_call_count: int,
        scrape_attempts: int,
        successful_scrapes: int,
        failed_scrapes: int,
        search_urls: list[str],
    ) -> str:
        """Return the research-mode instruction for the current phase."""
        url_hint = self._url_hint(search_urls)
        if scrape_attempts == 0 and tool_call_count <= 2:
            return (
                "\n\n=== DEEP RESEARCH WORKFLOW - PHASE 1: SCRAPE SOURCES ===\n"
                "You've completed initial searches. Now you MUST scrape the most relevant URLs.\n\n"
                "**YOUR NEXT ACTION:**\n"
                "Call `scrape_website` on 2-3 URLs from your search results above.\n"
                "IMPORTANT: Only use URLs that appeared in your search results!"
                f"{url_hint}\n"
                "**DO NOT** write a response yet. You need more detailed content first."
            )
        if scrape_attempts > 0 and successful_scrapes == 0 and failed_scrapes > 0:
            return (
                "\n\n=== DEEP RESEARCH WORKFLOW - SCRAPE ERROR RECOVERY ===\n"
                "Your previous scrape attempt failed. This is normal - some sites block scraping.\n\n"
                "**YOUR NEXT ACTION:**\n"
                "Try scraping DIFFERENT URLs from your search results.\n"
                "Choose URLs from different domains than the ones that failed."
                f"{url_hint}\n"
                "**DO NOT** give up. Try 2-3 more URLs before proceeding."
            )
        if successful_scrapes < 2 and tool_call_count < 8:
            return (
                "\n\n=== DEEP RESEARCH WORKFLOW - PHASE 2: EXPAND SOURCE COVERAGE ===\n"
                f"You've successfully scraped {successful_scrapes} source(s). Gather at least one or two more high-value sources before summarizing.\n\n"
                "**YOUR NEXT ACTION:**\n"
                "1. Call `scrape_website` on additional strong URLs from your search results\n"
                "2. Prefer sources that add new facts, dates, or perspectives\n\n"
                "**DO NOT** respond to the user yet. Strengthen the evidence first."
            )
        if successful_scrapes > 0:
            return (
                "\n\n=== DEEP RESEARCH WORKFLOW - PHASE 3: SYNTHESIZE & RESPOND ===\n"
                "You have enough source material to answer directly.\n\n"
                "**YOUR RESPONSE SHOULD INCLUDE:**\n"
                "1. A concise executive summary\n"
                "2. Key findings with source links or explicit source attribution\n"
                "3. Any important uncertainty, disagreement, or missing evidence\n"
                "4. A short conclusion or recommended next step if relevant\n\n"
                "**DO NOT** mention a generated document path. Respond with findings only."
            )
        return (
            "\n\n=== DEEP RESEARCH WORKFLOW - PHASE 4: COMPLETE ===\n"
            "Your research is complete. Provide a summary to the user.\n\n"
            "**YOUR RESPONSE SHOULD INCLUDE:**\n"
            "1. Key findings from your research\n"
            "2. A brief summary of your sources\n"
            "3. Any notable uncertainty or missing evidence\n\n"
            "**DO NOT** call more tools. Respond with your findings."
        )

    @staticmethod
    def _url_hint(search_urls: list[str]) -> str:
        """Return one formatted URL hint block for research mode."""
        if not search_urls:
            return ""
        url_hint = "\n\n**URLS FROM YOUR SEARCH RESULTS (use these!):**\n"
        for url in search_urls[:3]:
            url_hint += f"- {url}\n"
        return url_hint