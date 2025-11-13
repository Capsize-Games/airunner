"""Curiosity research mixin for DeepResearchAgent.

Handles curiosity-driven deep research and exploration.
"""

import re
import logging
from pathlib import Path
from typing import List, TypedDict

from airunner.components.llm.tools.research_document_tools import (
    append_research_notes,
)
from airunner.components.llm.tools.web_tools import (
    search_web,
    search_news,
    scrape_website,
)
from airunner.components.tools.web_content_extractor import WebContentExtractor
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


class DeepResearchState(TypedDict):
    """Type definition for deep research state."""

    messages: list
    current_phase: str
    research_topic: str
    clean_topic: str
    search_queries: list
    document_path: str
    notes_path: str
    scraped_urls: list


class CuriosityResearchMixin:
    """Provides curiosity-driven research methods."""

    def _read_notes_content(self, notes_path: str) -> str:
        """Read notes file content, returning empty string on error."""
        if not notes_path or not Path(notes_path).exists():
            return ""
        try:
            with open(notes_path, "r", encoding="utf-8") as f:
                content = f.read()
            logger.info(
                f"[Phase 1A-Curiosity] Read {len(content)} chars from notes"
            )
            return content
        except Exception as e:
            logger.error(f"[Phase 1A-Curiosity] Failed to read notes: {e}")
            return ""

    def _search_curiosity_topic(self, curiosity_topic: str) -> list:
        """Search web and news for a curiosity topic, returning combined results."""
        collected = []
        try:
            web_results = search_web(query=curiosity_topic)
            if isinstance(web_results, dict) and web_results.get("results"):
                collected.extend(web_results["results"])
        except Exception as e:
            logger.error(f"[Phase 1A-Curiosity] Web search failed: {e}")

        try:
            news_results = search_news(query=curiosity_topic)
            if isinstance(news_results, dict) and news_results.get("results"):
                collected.extend(news_results["results"])
        except Exception as e:
            logger.error(f"[Phase 1A-Curiosity] News search failed: {e}")

        return collected

    def _scrape_curiosity_result(
        self,
        item: dict,
        curiosity_topic: str,
        notes_path: str,
        already_scraped: set,
    ) -> tuple[bool, str | None]:
        """Scrape a single search result for curiosity research."""
        url = item.get("link") or item.get("url")
        if not url or self._is_domain_blacklisted(url):
            return False, None
        if url in already_scraped or self._is_url_irrelevant_path(url):
            return False, None

        try:
            result = scrape_website(url)
            if not result.get("content") or result.get("error"):
                return False, None

            content = result["content"]
            if not self._is_content_quality_acceptable(content):
                WebContentExtractor._add_to_blocklist(url)
                return False, None

            title = result.get("title") or item.get("title", "")
            findings = f"**CURIOSITY DEEP-DIVE: {curiosity_topic}**\n\nTitle: {title}\nURL: {url}\n\nExtract: {content[:3000]}"
            append_research_notes(
                notes_path=notes_path, source_url=url, findings=findings
            )
            return True, url
        except Exception as e:
            logger.warning(
                f"[Phase 1A-Curiosity] Scrape failed for {url}: {e}"
            )
            return False, None

    def _research_single_curiosity_topic(
        self,
        curiosity_topic: str,
        notes_path: str,
        already_scraped: set,
        max_per_topic: int,
    ) -> int:
        """Research a single curiosity topic, returning count of sources scraped."""
        logger.info(f"[Phase 1A-Curiosity] Deep dive: {curiosity_topic}")
        self._emit_progress(
            "Phase 1A-Curiosity", f"Deep dive: {curiosity_topic}"
        )

        collected = self._search_curiosity_topic(curiosity_topic)
        scraped_count = 0

        for item in collected:
            if scraped_count >= max_per_topic:
                break
            success, url = self._scrape_curiosity_result(
                item, curiosity_topic, notes_path, already_scraped
            )
            if success and url:
                scraped_count += 1
                already_scraped.add(url)
        return scraped_count

    def _phase1a_curiosity(self, state: DeepResearchState) -> dict:
        """Phase 1A-Curiosity: Extract interesting topics and research them deeper."""
        notes_path = state.get("notes_path", "")
        topic = state.get("clean_topic") or state.get("research_topic", "")

        logger.info(
            "[Phase 1A-Curiosity] Analyzing notes for interesting topics"
        )
        notes_content = self._read_notes_content(notes_path)
        if not notes_content:
            logger.warning("[Phase 1A-Curiosity] No notes content, skipping")
            return {
                "messages": state.get("messages", []),
                "current_phase": "phase1b",
            }

        curiosity_topics = self._extract_curiosity_topics(notes_content, topic)
        if not curiosity_topics:
            logger.info("[Phase 1A-Curiosity] No curiosity topics found")
            return {
                "messages": state.get("messages", []),
                "current_phase": "phase1b",
            }

        logger.info(
            f"[Phase 1A-Curiosity] Researching {len(curiosity_topics)} topics: {curiosity_topics}"
        )
        self._emit_progress(
            "Phase 1A-Curiosity",
            f"Researching {len(curiosity_topics)} deeper topics",
        )

        already_scraped = set(state.get("scraped_urls", []))
        total_scrapes = sum(
            self._research_single_curiosity_topic(
                topic, notes_path, already_scraped, 2
            )
            for topic in curiosity_topics[:5]
        )

        logger.info(
            f"[Phase 1A-Curiosity] Completed {total_scrapes} curiosity scrapes"
        )
        self._emit_progress(
            "Phase 1A-Curiosity",
            f"Completed deep dive ({total_scrapes} additional sources)",
        )

        return {
            "messages": state.get("messages", []),
            "current_phase": "phase1b",
            "scraped_urls": list(already_scraped),
        }

    @staticmethod
    def _extract_curiosity_topics(
        notes_content: str, base_topic: str
    ) -> List[str]:
        """Extract interesting topics from notes for deeper research."""
        curiosity_topics = []
        base_topic_lower = base_topic.lower()

        # Extract quoted terms (often key concepts)
        quoted_pattern = r'"([^"]{3,50})"'
        quoted_terms = re.findall(quoted_pattern, notes_content)
        for term in quoted_terms:
            term_lower = term.lower()
            # Skip if it's just the base topic
            if (
                term_lower != base_topic_lower
                and base_topic_lower not in term_lower
            ):
                curiosity_topics.append(term)

        # Extract proper nouns (capitalized words that aren't sentence starts)
        proper_noun_pattern = r"(?<=[.!?]\s)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)"
        proper_nouns = re.findall(proper_noun_pattern, notes_content)
        for noun in proper_nouns:
            noun_lower = noun.lower()
            # Skip common words and the base topic
            if (
                len(noun) > 3
                and noun_lower not in ["the", "this", "that", "these", "those"]
                and noun_lower != base_topic_lower
            ):
                curiosity_topics.append(noun)

        # Extract terms after key phrases
        key_phrases = [
            r"according to ([A-Z][a-z\s]+)",
            r"([A-Z][a-z\s]+) (?:said|stated|explained|noted)",
            r"(?:study|research|report) (?:by|from) ([A-Z][a-z\s]+)",
        ]
        for pattern in key_phrases:
            matches = re.findall(pattern, notes_content)
            curiosity_topics.extend(matches)

        # Deduplicate and limit
        seen = set()
        unique_topics = []
        for topic in curiosity_topics:
            topic_clean = topic.strip()
            if topic_clean and topic_clean not in seen:
                seen.add(topic_clean)
                unique_topics.append(topic_clean)

        return unique_topics[:10]  # Limit to top 10
