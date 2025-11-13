"""Curiosity research mixin for DeepResearchAgent.

Handles curiosity-driven deep research and exploration.
"""

import re
import logging
from typing import List, TypedDict

from airunner.components.llm.agents.deep_research.mixins.curiosity_search_mixin import (
    CuriositySearchMixin,
)
from airunner.components.llm.agents.deep_research.mixins.curiosity_extraction_mixin import (
    CuriosityExtractionMixin,
)

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


class CuriosityResearchMixin(CuriositySearchMixin, CuriosityExtractionMixin):
    """Provides curiosity-driven research orchestration."""

    def _research_single_curiosity_topic(
        self,
        curiosity_topic: str,
        notes_path: str,
        already_scraped: set,
        max_per_topic: int,
        main_topic: str,
        profile: dict | None = None,
    ) -> int:
        """Research a single curiosity topic with LLM fact extraction."""
        logger.info(f"[Phase 1A-Curiosity] Deep dive: {curiosity_topic}")
        self._emit_progress(
            "Phase 1A-Curiosity", f"Deep dive: {curiosity_topic}"
        )

        collected = self._search_curiosity_topic(curiosity_topic)
        scraped_count = 0

        for item in collected:
            if scraped_count >= max_per_topic:
                break

            # Pre-filter: Skip obviously irrelevant results
            if not self._is_search_result_relevant(
                item, curiosity_topic, main_topic, profile
            ):
                continue

            success, url = self._scrape_curiosity_result(
                item, curiosity_topic, notes_path, already_scraped, main_topic
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

        # Load and validate notes
        notes_content = self._read_notes_content(notes_path)
        if not notes_content:
            logger.warning("[Phase 1A-Curiosity] No notes content, skipping")
            return self._curiosity_skip_state(state)

        # Extract curiosity topics
        curiosity_topics = self._extract_curiosity_topics(notes_content, topic)
        if not curiosity_topics:
            logger.info("[Phase 1A-Curiosity] No curiosity topics found")
            return self._curiosity_skip_state(state)

        # Research curiosity topics
        already_scraped = set(state.get("scraped_urls", []))
        profile = (
            state.get("person_profile", {}) if isinstance(state, dict) else {}
        )
        total_scrapes = self._research_curiosity_topics(
            curiosity_topics, notes_path, already_scraped, topic, profile
        )

        # Update summary with findings
        self._finalize_curiosity_phase(notes_path, topic, total_scrapes)

        return {
            "messages": state.get("messages", []),
            "current_phase": "phase1b",
            "scraped_urls": list(already_scraped),
        }

    def _curiosity_skip_state(self, state: DeepResearchState) -> dict:
        """Return state when skipping curiosity phase."""
        return {
            "messages": state.get("messages", []),
            "current_phase": "phase1b",
        }

    def _research_curiosity_topics(
        self,
        curiosity_topics: list,
        notes_path: str,
        already_scraped: set,
        main_topic: str,
        profile: dict | None = None,
    ) -> int:
        """Research all curiosity topics and return total scrapes."""
        logger.info(
            f"[Phase 1A-Curiosity] Researching {len(curiosity_topics)} topics: {curiosity_topics}"
        )
        self._emit_progress(
            "Phase 1A-Curiosity",
            f"Researching {len(curiosity_topics)} deeper topics",
        )

        total_scrapes = sum(
            self._research_single_curiosity_topic(
                curiosity, notes_path, already_scraped, 2, main_topic, profile
            )
            for curiosity in curiosity_topics[:5]
        )

        logger.info(
            f"[Phase 1A-Curiosity] Completed {total_scrapes} curiosity scrapes"
        )
        self._emit_progress(
            "Phase 1A-Curiosity",
            f"Completed deep dive ({total_scrapes} additional sources)",
        )

        return total_scrapes

    def _finalize_curiosity_phase(
        self, notes_path: str, topic: str, total_scrapes: int
    ):
        """Finalize curiosity phase - logging only (summary stage disabled)."""
        logger.info(
            "[Phase 1A-Curiosity] Finalizing curiosity phase - summary update removed"
        )

    @staticmethod
    def _extract_curiosity_topics(
        notes_content: str, base_topic: str
    ) -> List[str]:
        """Extract topics from 'More research required' sections in notes."""
        curiosity_topics = []

        # Pattern: #### More research required\n- Topic\n- Another topic
        pattern = r"#### More research required\s*\n((?:- .+\n?)+)"
        matches = re.findall(pattern, notes_content, re.MULTILINE)

        for match in matches:
            lines = match.strip().split("\n")
            for line in lines:
                topic = line.strip().lstrip("- ").strip()
                if topic and len(topic) > 5:
                    curiosity_topics.append(topic)

        # Deduplicate while preserving order
        seen = set()
        unique_topics = []
        for topic in curiosity_topics:
            topic_lower = topic.lower()
            if topic_lower not in seen and len(topic_lower) > 5:
                seen.add(topic_lower)
                unique_topics.append(topic)

        logger.info(
            f"[Curiosity] Extracted {len(unique_topics)} topics from 'More research required' sections"
        )
        return unique_topics[:10]
