"""Search and gather mixin for DeepResearchAgent.

Handles initial search, filtering, and source gathering for research.
"""

import logging
from pathlib import Path
from typing import TypedDict

from airunner.components.llm.tools.research_document_tools import (
    create_research_document,
    append_research_notes,
)
from airunner.components.llm.tools.web_tools import (
    search_web,
    search_news,
    scrape_website,
)
from airunner.components.tools.web_content_extractor import WebContentExtractor

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


class SearchGatherMixin:
    """Provides search and initial gathering methods."""

    def _create_research_files(self, topic: str, state: dict) -> dict:
        """Create research document and notes files."""
        try:
            # CRITICAL: Pass api parameter to avoid "Error: API not available"
            doc_path = create_research_document(topic=topic, api=self._api)

            # Validate the document path before proceeding
            if not doc_path or "Error" in doc_path:
                logger.error(f"Document creation failed: {doc_path}")
                raise ValueError(f"Invalid document path: {doc_path}")

            # Create notes file alongside the document
            notes_path = Path(doc_path).with_suffix(".notes.md")
            notes_path.touch(exist_ok=True)

            logger.info(
                f"Created research files: {doc_path}, notes: {notes_path}"
            )
            return {
                "document_path": str(doc_path),
                "notes_path": str(notes_path),
            }
        except Exception as e:
            logger.error(
                f"Failed to create research files: {e}", exc_info=True
            )
            # Return state unchanged - this will cause later phases to fail gracefully
            return {}

    def _run_searches(self, query: str) -> list:
        """Run web and news searches, return combined results."""
        collected = []

        try:
            web_results = search_web(query=query)
            if isinstance(web_results, dict) and web_results.get("results"):
                collected.extend(web_results["results"])
                logger.info(
                    f"[Phase 1A] Found {len(web_results['results'])} web results"
                )
        except Exception as e:
            logger.error(f"[Phase 1A] Web search failed: {e}")

        try:
            news_results = search_news(query=query)
            if isinstance(news_results, dict) and news_results.get("results"):
                collected.extend(news_results["results"])
                logger.info(
                    f"[Phase 1A] Found {len(news_results['results'])} news results"
                )
        except Exception as e:
            logger.error(f"[Phase 1A] News search failed: {e}")

        return collected

    def _filter_search_results(
        self, collected: list, topic: str, already_scraped: set
    ) -> list:
        """Deduplicate and filter search results for relevance."""
        seen = set()
        filtered = []
        topic_lower = topic.lower()

        for item in collected:
            url = item.get("link") or item.get("url")
            if not url or url in seen or url in already_scraped:
                continue

            if self._is_domain_blacklisted(url):
                logger.info(f"[Phase 1A] Skipping blacklisted domain: {url}")
                continue

            if self._is_url_irrelevant_path(url):
                logger.info(f"[Phase 1A] Skipping irrelevant URL path: {url}")
                continue

            seen.add(url)

            title = (item.get("title") or "").lower()
            snippet = (item.get("snippet") or "").lower()
            topic_words = topic_lower.split()

            # Determine relevance based on topic word presence
            topic_match_count = sum(
                1 for word in topic_words if word in title or word in snippet
            )
            relevance_score = topic_match_count / max(len(topic_words), 1)

            # Only include if at least 50% of topic words are present
            if relevance_score >= 0.5:
                item["_relevance"] = relevance_score
                filtered.append(item)

        # Sort by relevance score (highest first)
        filtered.sort(key=lambda x: x.get("_relevance", 0), reverse=True)
        logger.info(
            f"[Phase 1A] Filtered {len(collected)} results to {len(filtered)} relevant ones"
        )

        return filtered

    def _scrape_and_note_sources(
        self,
        filtered: list,
        notes_path: str,
        max_sources: int,
        already_scraped: set,
    ) -> int:
        """Scrape filtered sources and append findings to notes."""
        scraped_count = 0

        for item in filtered:
            if scraped_count >= max_sources:
                break

            url = item.get("link") or item.get("url")
            if not url or url in already_scraped:
                continue

            try:
                result = scrape_website(url)

                # Check if we got an error
                if not result.get("content") or result.get("error"):
                    logger.warning(
                        f"[Phase 1A] Scraper error for {url}: {result.get('error', 'Unknown')}"
                    )
                    continue

                content = result["content"]
                page_title = result.get("title")

                # Validate content quality
                if not self._is_content_quality_acceptable(content):
                    logger.warning(
                        f"[Phase 1A] Content quality too low for {url} - adding to blocklist"
                    )
                    # Add to blocklist to avoid this domain in the future
                    WebContentExtractor._add_to_blocklist(url)
                    continue

                # Use page title if available, fallback to search result title
                title = page_title or item.get("title", "")

                # Append to research notes
                findings = (
                    f"Title: {title}\nURL: {url}\n\nExtract: {content[:3000]}"
                )
                append_research_notes(
                    notes_path=notes_path,
                    source_url=url,
                    findings=findings,
                )
                scraped_count += 1
                already_scraped.add(url)

                self._emit_progress(
                    "Phase 1A",
                    f"Scraped {scraped_count}/{max_sources} sources",
                )

            except Exception as e:
                logger.warning(f"[Phase 1A] Scrape failed for {url}: {e}")
                continue

        return scraped_count

    def _phase1a_gather(self, state: DeepResearchState) -> dict:
        """Phase 1A: Gather initial sources by executing search queries."""
        queries = state.get("search_queries", [])
        topic = state.get("clean_topic") or state.get("research_topic", "")

        logger.info(
            f"[Phase 1A] Gathering sources with {len(queries)} queries"
        )

        # Create files if needed
        state_updates = self._create_research_files(topic, state)
        notes_path = state_updates.get("notes_path") or state.get(
            "notes_path", ""
        )
        document_path = state_updates.get("document_path") or state.get(
            "document_path", ""
        )

        if not notes_path:
            logger.error("[Phase 1A] No notes path available")
            return {
                "messages": state.get("messages", []),
                "current_phase": "phase1a-curiosity",
                **state_updates,
            }

        # Get already-scraped URLs to avoid duplicates
        already_scraped = set(state.get("scraped_urls", []))

        # Run searches and collect results
        all_collected = []
        for query in queries:
            logger.info(f"[Phase 1A] Searching: {query}")
            self._emit_progress("Phase 1A", f"Searching: {query}")
            collected = self._run_searches(query)
            all_collected.extend(collected)

        # Filter and deduplicate
        filtered = self._filter_search_results(
            all_collected, topic, already_scraped
        )

        # Scrape top sources
        max_sources = 10
        scraped_count = self._scrape_and_note_sources(
            filtered, notes_path, max_sources, already_scraped
        )

        logger.info(f"[Phase 1A] Gathered {scraped_count} sources")
        self._emit_progress(
            "Phase 1A", f"Gathered {scraped_count} initial sources"
        )

        # Update state
        state_updates.update(
            {
                "sources_scraped": scraped_count,
                "scraped_urls": list(already_scraped),
            }
        )

        return {
            "messages": state.get("messages", []),
            "current_phase": "phase1a-curiosity",
            **state_updates,
        }
