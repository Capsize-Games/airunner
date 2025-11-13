"""Curiosity search mixin for DeepResearchAgent.

Handles search and scraping for curiosity-driven research.
"""

import re
import logging
from pathlib import Path
from typing import List

from airunner.components.tools.web_content_extractor import WebContentExtractor

logger = logging.getLogger(__name__)


class CuriositySearchMixin:
    """Provides curiosity search and scraping methods."""

    @staticmethod
    def _extract_topic_keywords(topic: str) -> List[str]:
        """Extract key terms from main topic for validation."""
        words = re.split(r"[\s\-_,;:]+", topic.lower())

        stopwords = {
            "and",
            "or",
            "the",
            "a",
            "an",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "his",
            "her",
            "their",
        }
        keywords = [
            w for w in words if w and len(w) > 2 and w not in stopwords
        ]

        # Add variations for proper nouns
        extended_keywords = keywords.copy()
        for kw in keywords:
            if kw == "syria":
                extended_keywords.extend(["syrian", "damascus"])
            elif kw == "trump":
                extended_keywords.extend(["donald", "president"])

        return extended_keywords

    def _read_notes_content(self, notes_path: str) -> str:
        """Read notes file content."""
        if not notes_path or not Path(notes_path).exists():
            return ""
        try:
            with open(notes_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"[Curiosity] Failed to read notes: {e}")
            return ""

    def _search_curiosity_topic(self, curiosity_topic: str) -> list:
        """Search for curiosity topic and return results."""
        from airunner.components.llm.tools.web_tools import (
            search_web,
            search_news,
        )

        logger.info(
            f"[Phase 1A-Curiosity] Searching curiosity topic: {curiosity_topic}"
        )

        # search_web and search_news return formatted strings, not lists
        # We need to use AggregatedSearchTool directly for list results
        try:
            from airunner.components.tools.search_tool import (
                AggregatedSearchTool,
            )

            search_tool = AggregatedSearchTool()
            web_results = search_tool.search(curiosity_topic, max_results=10)
            news_results = search_tool.search_news(
                curiosity_topic, max_results=5
            )

            all_results = (web_results or []) + (news_results or [])
            return all_results[:15]
        except Exception as e:
            logger.error(
                f"[Phase 1A-Curiosity] Search failed for '{curiosity_topic}': {e}"
            )
            return []

    def _scrape_curiosity_result(
        self,
        item: dict,
        curiosity_topic: str,
        notes_path: str,
        already_scraped: set,
        main_topic: str,
    ) -> tuple[bool, str | None]:
        """Scrape a single search result for curiosity research."""
        url = item.get("link") or item.get("url")
        if not url or self._is_domain_blacklisted(url):
            return False, None
        if url in already_scraped or self._is_url_irrelevant_path(url):
            return False, None

        try:
            from airunner.components.tools.web_content_extractor import (
                WebContentExtractor,
            )

            result = WebContentExtractor.fetch_and_extract_with_metadata_raw(
                url, use_cache=True, summarize=False
            )

            if not result or not result.get("content") or result.get("error"):
                return False, None

            raw_content = result["content"]

            # Validate content
            if not self._validate_curiosity_content(raw_content, url):
                return False, None

            # Extract and validate facts
            title = result.get("title") or item.get("title", "")
            metadata = self._build_metadata_dict(result)

            extracted_facts = self._extract_curiosity_facts_with_llm(
                raw_content, curiosity_topic, main_topic, url, title, metadata
            )

            if not extracted_facts:
                logger.info(f"[Phase 1A-Curiosity] No relevant facts in {url}")
                return False, None

            # Save note
            self._save_curiosity_note(
                notes_path,
                curiosity_topic,
                title,
                url,
                metadata,
                extracted_facts,
            )
            return True, url

        except Exception as e:
            logger.warning(
                f"[Phase 1A-Curiosity] Scrape failed for {url}: {e}"
            )
            return False, None

    def _validate_curiosity_content(self, raw_content: str, url: str) -> bool:
        """Validate content quality for curiosity research."""
        from airunner.components.tools.web_content_extractor import (
            WebContentExtractor,
        )

        if not self._is_content_quality_acceptable(raw_content):
            WebContentExtractor._add_to_blocklist(url)
            return False

        if self._is_structured_data(raw_content):
            logger.info(
                f"[Phase 1A-Curiosity] Skipping structured data from {url}"
            )
            return False

        return True

    def _build_metadata_dict(self, result: dict) -> dict:
        """Build metadata dictionary from scrape result."""
        return {
            "author": result.get("author"),
            "publish_date": result.get("publish_date"),
            "description": result.get("description"),
        }

    def _save_curiosity_note(
        self,
        notes_path: str,
        curiosity_topic: str,
        title: str,
        url: str,
        metadata: dict,
        facts: str,
    ):
        """Save curiosity research note to file."""
        from urllib.parse import urlparse
        from datetime import datetime

        domain = urlparse(url).netloc
        publish_date = metadata.get("publish_date") or "Unknown"

        if publish_date != "Unknown" and isinstance(publish_date, str):
            for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%B %d, %Y"]:
                try:
                    dt = datetime.strptime(publish_date, fmt)
                    publish_date = dt.strftime("%Y-%m-%d")
                    break
                except:
                    continue

        structured_note = f"""### [CURIOSITY DEEP-DIVE: {curiosity_topic}] {title} [{domain}]({url})
**Published: {publish_date}**

{facts}

---

"""
        with open(notes_path, "a", encoding="utf-8") as f:
            f.write(structured_note)

    def _is_search_result_relevant(
        self,
        item: dict,
        curiosity_topic: str,
        main_topic: str,
        profile: dict | None = None,
    ) -> bool:
        """Check if search result is potentially relevant to curiosity topic."""
        title = (item.get("title") or "").lower()
        snippet = (
            item.get("snippet") or item.get("description") or ""
        ).lower()
        combined_text = f"{title} {snippet}"

        # Extract topic keywords
        curiosity_keywords = self._extract_topic_keywords(curiosity_topic)
        main_keywords = self._extract_topic_keywords(main_topic)

        # Count keyword matches
        curiosity_matches = sum(
            1 for kw in curiosity_keywords if kw in combined_text
        )
        main_matches = sum(1 for kw in main_keywords if kw in combined_text)

        # Require at least one curiosity match AND one main topic match
        relevant = curiosity_matches > 0 and main_matches > 0

        # If we have a person profile and the snippet mentions an age, compare.
        if profile and profile.get("approximate_age") and relevant:
            try:
                page_age = None
                if combined_text:
                    page_age = self._extract_approximate_age_from_text(
                        combined_text
                    )
                if page_age:
                    profile_age = int(profile.get("approximate_age"))
                    # If ages differ widely (>= 20 years), it's likely a different person
                    if abs(page_age - profile_age) >= 20:
                        logger.info(
                            f"[Phase 1A-Curiosity] Age mismatch (profile {profile_age} vs page {page_age}) - likely different person"
                        )
                        return False
            except Exception:
                pass
        return relevant
